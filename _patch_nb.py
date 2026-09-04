"""
Speed patch for DegreeDetailExtract_Training.ipynb.

Changes:
  Cell 16 (cell-s3-tokens)  : Reduce processor image size to 640x480 (4x fewer attention ops)
  Cell 18 (cell-s3-train)   : Reduce grad_accum 16→8, epochs 15→8, eval/save steps 500→1000
"""

import json

NB_PATH = 'DegreeDetailExtract_Training.ipynb'
nb = json.load(open(NB_PATH, encoding='utf-8'))

# ── Cell 16 (cell-s3-tokens): add image size reduction after model load ───────
S3_TOKENS_SRC = """\
import gc, torch
from transformers import DonutProcessor, VisionEncoderDecoderModel

# Free the CORD smoke-test model from GPU memory before loading a fresh one.
try:
    del model, processor
    gc.collect()
    torch.cuda.empty_cache()
    print("Cleared previous model from VRAM.")
except NameError:
    pass

print("Loading fresh donut-base ...")
processor = DonutProcessor.from_pretrained('naver-clova-ix/donut-base')
model     = VisionEncoderDecoderModel.from_pretrained('naver-clova-ix/donut-base')

# ── Reduce image resolution: 1280x960 -> 640x480 ─────────────────────────────
# The Swin attention is O(n^2) in image size. Half the resolution = 4x fewer
# attention operations = ~3-4x faster training with only a small accuracy trade-off.
# For a class project / proof-of-concept this is the right trade-off on free T4.
IMG_H, IMG_W = 640, 480
processor.image_processor.size = {"height": IMG_H, "width": IMG_W}
model.config.encoder.image_size = [IMG_H, IMG_W]
print(f"Image size set to {IMG_H}x{IMG_W} (down from 1280x960)")

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
print(f"Tokeniser vocab size: {len(processor.tokenizer)}")
"""

# ── Cell 18 (cell-s3-train): speed + memory tuning ───────────────────────────
S3_TRAIN_SRC = """\
import os, torch
from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
model.gradient_checkpointing_enable()
torch.cuda.empty_cache()


def collate_fn(batch):
    return {
        'pixel_values': torch.stack([b['pixel_values'] for b in batch]),
        'labels':       torch.stack([b['labels']       for b in batch]),
    }


# ── Estimated training time with these settings on a free T4 ─────────────────
# Steps per epoch = len(train_ds) / effective_batch = 4000 / 8 = 500
# Total steps     = 500 x 8 epochs = 4000
# Speed (640x480 + gc + adafactor) ~ 0.12-0.18 it/s  =>  ~6-9 hrs
# -> fits within a Colab Pro session; borderline for free (save checkpoints often)
# ─────────────────────────────────────────────────────────────────────────────
training_args = Seq2SeqTrainingArguments(
    output_dir=CKPT_PATH,
    # -- Epochs: 8 is enough for synthetic data to converge ---------------------
    num_train_epochs=8,
    # -- Batch: bs=1, accum=8 -> effective batch 8 (was 16 with accum=16) ------
    # Halving accum_steps halves the wall-clock time per update step.
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    per_device_eval_batch_size=1,
    # -- Optimiser ---------------------------------------------------------------
    optim='adafactor',      # ~3x less memory than AdamW
    learning_rate=5e-5,
    weight_decay=0.01,
    warmup_steps=300,
    # -- Mixed precision + memory ------------------------------------------------
    fp16=True,
    gradient_checkpointing=True,
    # -- Logging: less frequent to reduce overhead --------------------------------
    logging_steps=100,
    eval_strategy='steps',
    eval_steps=1000,        # evaluate less often (Drive write is slow)
    # -- Checkpointing -----------------------------------------------------------
    save_strategy='steps',
    save_steps=1000,        # save less often (Drive write is slow)
    save_total_limit=3,
    load_best_model_at_end=True,
    metric_for_best_model='eval_loss',
    greater_is_better=False,
    # -- Misc --------------------------------------------------------------------
    predict_with_generate=False,
    report_to='none',
    dataloader_num_workers=4,   # more workers to keep GPU fed
    remove_unused_columns=False,
)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    data_collator=collate_fn,
)

eff_batch = training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps
steps_per_epoch = len(train_ds) // eff_batch
total_steps     = steps_per_epoch * training_args.num_train_epochs

print('Starting fine-tuning...')
print(f'Steps per epoch (eff.): {steps_per_epoch}')
print(f'Total steps            : {total_steps}')
print(f'Total epochs           : {training_args.num_train_epochs}')
print(f'Effective batch size   : {eff_batch}')
print(f'Optimiser              : {training_args.optim}')
print(f'Image size             : 640x480')
print(f'Checkpoints            -> {CKPT_PATH}\\n')

trainer.train()

best_ckpt = f'{CKPT_PATH}/best_model'
trainer.save_model(best_ckpt)
processor.save_pretrained(best_ckpt)
print(f'\\nBest model saved to {best_ckpt}')
"""

PATCHES = {
    'cell-s3-tokens': S3_TOKENS_SRC,
    'cell-s3-train':  S3_TRAIN_SRC,
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
    print("ERROR: No cells matched.")
else:
    with open(NB_PATH, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f"Patched {len(patched)} cells:")
    for p in patched:
        print(p)
    print("\nNotebook saved.")
