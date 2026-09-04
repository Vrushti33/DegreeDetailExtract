"""
Patch DegreeDetailExtract_Training.ipynb with three fixes:

1. Cell 9  (cell-s1-drive-copy)  : zip dataset → copy 1 file instead of 5,000
2. Cell 16 (cell-s3-tokens)      : free CORD model from VRAM before reloading
3. Cell 17 (cell-s3-dataset)     : unzip from Drive to local SSD before training
4. Cell 18 (cell-s3-train)       : fix OOM — batch=1, accum=16, adafactor, env var
"""

import json

NB_PATH = 'DegreeDetailExtract_Training.ipynb'
nb = json.load(open(NB_PATH, encoding='utf-8'))

# ─────────────────────────────────────────────────────────────────────────────
# Cell 9 — Drive copy: zip first, copy one file
# ─────────────────────────────────────────────────────────────────────────────
DRIVE_COPY_SRC = """\
import shutil, os

# Compress the dataset into a single zip file.
# Copying 1 file to Drive is ~20x faster than copying 5,000 individual images.
print("Compressing dataset (1-2 min) ...")
zip_src = '/content/dataset_archive'
shutil.make_archive(zip_src, 'zip', '/content', 'dataset')
zip_gb  = os.path.getsize(zip_src + '.zip') / 1e9
print(f"Zip created: {zip_gb:.2f} GB")

# Copy the single zip to Drive
dest_zip = f'{DRIVE_PATH}/dataset_archive.zip'
print(f"Uploading to Drive: {dest_zip} ...")
shutil.copy(zip_src + '.zip', dest_zip)
print("Dataset zip saved to Drive.")

# Also copy the small metadata jsonl files separately (handy for quick access)
for split in ('train', 'val', 'test'):
    src = f'/content/dataset/metadata_{split}.jsonl'
    dst = f'{DRIVE_PATH}/metadata_{split}.jsonl'
    shutil.copy(src, dst)
    n = sum(1 for _ in open(src))
    print(f"  {split}: {n:,} records saved.")
"""

# ─────────────────────────────────────────────────────────────────────────────
# Cell 16 — Free CORD model from VRAM before loading fresh model for Section 3
# ─────────────────────────────────────────────────────────────────────────────
S3_TOKENS_SRC = """\
import gc, torch
from transformers import DonutProcessor, VisionEncoderDecoderModel

# Free the CORD smoke-test model from GPU memory before loading a fresh one.
# Without this, both models compete for the T4's 15 GB and cause OOM.
try:
    del model, processor
    gc.collect()
    torch.cuda.empty_cache()
    print("Cleared previous model from VRAM.")
except NameError:
    pass  # first run -- nothing to clear

# Reload a clean base model for certificate fine-tuning
print("Loading fresh donut-base ...")
processor = DonutProcessor.from_pretrained('naver-clova-ix/donut-base')
model     = VisionEncoderDecoderModel.from_pretrained('naver-clova-ix/donut-base')

# Special tokens for the 7 certificate fields
CERT_SPECIAL_TOKENS = [
    '<s_cert>', '</s_cert>',
    '<s_student_name>',    '</s_student_name>',
    '<s_university_name>', '</s_university_name>',
    '<s_course_name>',     '</s_course_name>',
    '<s_specialization>',  '</s_specialization>',
    '<s_pass_class>',      '</s_pass_class>',
    '<s_authority_name>',  '</s_authority_name>',
    '<s_issue_date>',      '</s_issue_date>',
]

processor.tokenizer.add_special_tokens(
    {'additional_special_tokens': CERT_SPECIAL_TOKENS}
)
model.decoder.resize_token_embeddings(len(processor.tokenizer))

model.config.decoder_start_token_id = processor.tokenizer.convert_tokens_to_ids('<s_cert>')
model.config.pad_token_id           = processor.tokenizer.pad_token_id
model.config.eos_token_id           = processor.tokenizer.eos_token_id

model.to(DEVICE)
print(f"Special tokens added ({len(CERT_SPECIAL_TOKENS)} new tokens).")
print(f"Tokenizer vocab size: {len(processor.tokenizer)}")
"""

# ─────────────────────────────────────────────────────────────────────────────
# Cell 17 — Unzip dataset to local Colab SSD before training
# ─────────────────────────────────────────────────────────────────────────────
S3_DATASET_SRC = """\
import json, os, shutil
from pathlib import Path
from PIL import Image
from torch.utils.data import Dataset

# Unzip dataset from Drive to local Colab SSD if not already present.
# Reading images from local SSD during training is ~10x faster than reading
# from the Drive FUSE mount.
LOCAL_DATASET = '/content/dataset'
if not os.path.exists(LOCAL_DATASET):
    print("Unzipping dataset from Drive to local storage ...")
    shutil.unpack_archive(f'{DRIVE_PATH}/dataset_archive.zip', '/content')
    print("Done.")
else:
    print("Dataset already available locally -- skipping unzip.")

DATASET_PATH = LOCAL_DATASET   # override to local path for training

CERT_MAX_LENGTH = 512
FIELD_NAMES = [
    'student_name', 'university_name', 'course_name',
    'specialization', 'pass_class', 'authority_name', 'issue_date',
]


def fields_to_target(fields: dict) -> str:
    inner = ''.join(
        f'<s_{f}>{fields.get(f, "")}</s_{f}>'
        for f in FIELD_NAMES
    )
    return f'<s_cert>{inner}</s_cert>'


def load_metadata(jsonl_path: str) -> list:
    with open(jsonl_path, encoding='utf-8') as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


class CertificateDataset(Dataset):
    def __init__(self, records: list, dataset_root: str):
        self.records = records
        self.root    = Path(dataset_root)

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        rec   = self.records[idx]
        image = Image.open(self.root / rec['file_name']).convert('RGB')

        pixel_values = processor(image, return_tensors='pt').pixel_values.squeeze()
        target       = fields_to_target(rec)

        input_ids = processor.tokenizer(
            target,
            add_special_tokens=False,
            max_length=CERT_MAX_LENGTH,
            padding='max_length',
            truncation=True,
            return_tensors='pt',
        ).input_ids.squeeze()

        labels = input_ids.clone()
        labels[labels == processor.tokenizer.pad_token_id] = -100

        return {'pixel_values': pixel_values, 'labels': labels}


print('Loading dataset splits ...')
train_records = load_metadata(f'{DATASET_PATH}/metadata_train.jsonl')
val_records   = load_metadata(f'{DATASET_PATH}/metadata_val.jsonl')
test_records  = load_metadata(f'{DATASET_PATH}/metadata_test.jsonl')

train_ds = CertificateDataset(train_records, DATASET_PATH)
val_ds   = CertificateDataset(val_records,   DATASET_PATH)
test_ds  = CertificateDataset(test_records,  DATASET_PATH)

print(f'Train: {len(train_ds):,}  |  Val: {len(val_ds):,}  |  Test: {len(test_ds):,}')
print('\\nSample target string:')
print(fields_to_target(train_records[0]))
"""

# ─────────────────────────────────────────────────────────────────────────────
# Cell 18 — Training: fix OOM (bs=1, accum=16, adafactor, env var)
# ─────────────────────────────────────────────────────────────────────────────
S3_TRAIN_SRC = """\
import os, torch
from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

# Allocator: reduces fragmentation-related OOM
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

# Gradient checkpointing: trades ~20% speed for ~35% less VRAM
model.gradient_checkpointing_enable()

# Clear any leftover allocations before the trainer starts
torch.cuda.empty_cache()


def collate_fn(batch):
    return {
        'pixel_values': torch.stack([b['pixel_values'] for b in batch]),
        'labels':       torch.stack([b['labels']       for b in batch]),
    }


training_args = Seq2SeqTrainingArguments(
    output_dir=CKPT_PATH,
    # -- Volume ------------------------------------------------------------------
    num_train_epochs=15,
    # -- Batch: bs=1, accum=16 -> effective batch 16 (same as before) -----------
    # Donut's Swin-B encoder is very deep; bs=2 exhausts the T4's 15 GB VRAM.
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16,
    per_device_eval_batch_size=1,
    # -- Optimiser ---------------------------------------------------------------
    # Adafactor uses ~3x less memory than AdamW (no first/second moment vectors).
    optim='adafactor',
    learning_rate=5e-5,
    weight_decay=0.01,
    warmup_steps=500,
    # -- Mixed precision + memory ------------------------------------------------
    fp16=True,
    gradient_checkpointing=True,
    # -- Logging & evaluation ----------------------------------------------------
    logging_steps=50,
    eval_strategy='steps',
    eval_steps=500,
    # -- Checkpointing (Drive survives Colab session resets) ---------------------
    save_strategy='steps',
    save_steps=500,
    save_total_limit=3,
    load_best_model_at_end=True,
    metric_for_best_model='eval_loss',
    greater_is_better=False,
    # -- Misc --------------------------------------------------------------------
    predict_with_generate=False,
    report_to='none',
    dataloader_num_workers=2,
    remove_unused_columns=False,
)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    data_collator=collate_fn,
)

print('Starting fine-tuning...')
print(f'Steps per epoch (eff.): {len(train_ds) // 16}')
print(f'Total epochs           : {training_args.num_train_epochs}')
print(f'Effective batch size   : {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}')
print(f'Optimiser              : {training_args.optim}')
print(f'Checkpoints            -> {CKPT_PATH}\\n')

trainer.train()

best_ckpt = f'{CKPT_PATH}/best_model'
trainer.save_model(best_ckpt)
processor.save_pretrained(best_ckpt)
print(f'\\nBest model saved to {best_ckpt}')
"""

# ─────────────────────────────────────────────────────────────────────────────
# Apply all patches
# ─────────────────────────────────────────────────────────────────────────────
PATCHES = {
    'cell-s1-drive-copy': DRIVE_COPY_SRC,
    'cell-s3-tokens':     S3_TOKENS_SRC,
    'cell-s3-dataset':    S3_DATASET_SRC,
    'cell-s3-train':      S3_TRAIN_SRC,
}

patched = []
for i, cell in enumerate(nb['cells']):
    cid = cell.get('id', '')
    if cid in PATCHES:
        src = PATCHES[cid]
        cell['source'] = [ln + '\n' for ln in src.splitlines()]
        cell['source'][-1] = cell['source'][-1].rstrip('\n')
        patched.append(f'  Cell {i:2d} ({cid})')

if not patched:
    print("ERROR: No cells matched. Check cell IDs.")
else:
    with open(NB_PATH, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f"Patched {len(patched)} cells:")
    for p in patched:
        print(p)
    print("\nNotebook saved.")
