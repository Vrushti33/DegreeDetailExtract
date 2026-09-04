"""
Patch DegreeDetailExtract_Training.ipynb:

1. Cell 13 (cell-s2-cord-train): 
   - Fix deprecated torch.cuda.amp.* -> torch.amp.*
   - Reduce batch_size 2 -> 1
   - Add gradient checkpointing + cache clear
   - Use optimizer.zero_grad(set_to_none=True)

2. Cell 18 (cell-s3-train):
   - Add gradient_checkpointing=True to Seq2SeqTrainingArguments
   - Add model.gradient_checkpointing_enable() before trainer creation
"""

import json, re

NB_PATH = 'DegreeDetailExtract_Training.ipynb'

with open(NB_PATH, encoding='utf-8') as f:
    nb = json.load(f)

# ── Patch cell 13: CORD smoke-test training loop ──────────────────────────────
NEW_CORD_TRAIN_SOURCE = """\
import torch
import os
from torch.utils.data import DataLoader
from torch.optim import AdamW

# ── Memory: set allocator config BEFORE any CUDA allocation ───────────────────
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
torch.cuda.empty_cache()

# Gradient checkpointing: trades compute for memory (essential on T4 + Donut)
if hasattr(model, 'gradient_checkpointing_enable'):
    model.gradient_checkpointing_enable()

CORD_STEPS = 200
LR         = 5e-5

def collate_fn(batch):
    return {
        'pixel_values': torch.stack([b['pixel_values'] for b in batch]),
        'labels':       torch.stack([b['labels']       for b in batch]),
    }

# batch_size=1: Donut's Swin encoder is large; bs=2 OOMs the T4's 15 GB
loader    = DataLoader(cord_train, batch_size=1, shuffle=True, collate_fn=collate_fn)
optimizer = AdamW(model.parameters(), lr=LR)

# torch.amp (updated API — torch.cuda.amp.* is deprecated in PyTorch >= 2.3)
use_amp = (DEVICE == 'cuda')
scaler  = torch.amp.GradScaler('cuda', enabled=use_amp)

model.train()
step, losses = 0, []

for batch in loader:
    pixel_values = batch['pixel_values'].to(DEVICE)
    labels       = batch['labels'].to(DEVICE)

    with torch.amp.autocast('cuda', enabled=use_amp):
        outputs = model(pixel_values=pixel_values, labels=labels)
        loss    = outputs.loss

    scaler.scale(loss).backward()
    scaler.step(optimizer)
    scaler.update()
    optimizer.zero_grad(set_to_none=True)  # set_to_none frees grad buffers immediately

    losses.append(loss.item())
    step += 1
    if step % 50 == 0:
        avg = sum(losses[-50:]) / len(losses[-50:])
        print(f'Step {step:4d} / {CORD_STEPS} | loss: {avg:.4f}')
    if step >= CORD_STEPS:
        break

print(f'\\nCORD smoke test complete. Final loss: {losses[-1]:.4f}')
print('Loss should have decreased from the initial value -- if so, the pipeline is working.')
"""

# ── Patch cell 18: Seq2SeqTrainer (certificate fine-tuning) ──────────────────
# Find the cell with Seq2SeqTrainingArguments and patch it
NEW_S3_TRAIN_SOURCE = """\
from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

# Gradient checkpointing: saves ~30-40% VRAM at the cost of ~20% extra compute
model.gradient_checkpointing_enable()

def collate_fn(batch):
    return {
        'pixel_values': torch.stack([b['pixel_values'] for b in batch]),
        'labels':       torch.stack([b['labels']       for b in batch]),
    }

training_args = Seq2SeqTrainingArguments(
    output_dir=CKPT_PATH,
    # -- Volume -------------------------------------------------------------------
    num_train_epochs=15,
    # -- Batch (T4 16 GB: bs=2, grad-accum=8 -> effective bs=16) ----------------
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    per_device_eval_batch_size=2,
    # -- Optimiser ----------------------------------------------------------------
    learning_rate=5e-5,
    weight_decay=0.01,
    warmup_steps=500,
    # -- Mixed precision + memory -------------------------------------------------
    fp16=True,
    gradient_checkpointing=True,
    # -- Logging & evaluation -----------------------------------------------------
    logging_steps=50,
    eval_strategy='steps',
    eval_steps=500,
    # -- Checkpointing (saves to Drive -- survives session resets) ----------------
    save_strategy='steps',
    save_steps=500,
    save_total_limit=3,
    load_best_model_at_end=True,
    metric_for_best_model='eval_loss',
    greater_is_better=False,
    # -- Misc ---------------------------------------------------------------------
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
print(f'Total epochs: {training_args.num_train_epochs}')
print(f'Checkpoints -> {CKPT_PATH}\\n')

trainer.train()

# Save the best model explicitly to Drive
best_ckpt = f'{CKPT_PATH}/best_model'
trainer.save_model(best_ckpt)
processor.save_pretrained(best_ckpt)
print(f'\\nBest model saved to {best_ckpt}')
"""

# ── Apply patches ─────────────────────────────────────────────────────────────
patched = 0
for i, cell in enumerate(nb['cells']):
    src = ''.join(cell.get('source', []))
    cid = cell.get('id', '')

    if cid == 'cell-s2-cord-train' or (i == 13 and 'GradScaler' in src):
        cell['source'] = [line + '\n' for line in NEW_CORD_TRAIN_SOURCE.splitlines()]
        cell['source'][-1] = cell['source'][-1].rstrip('\n')
        print(f'Patched cell {i} (CORD training loop)')
        patched += 1

    elif cid == 'cell-s3-train' or (i == 18 and 'Seq2SeqTrainingArguments' in src):
        cell['source'] = [line + '\n' for line in NEW_S3_TRAIN_SOURCE.splitlines()]
        cell['source'][-1] = cell['source'][-1].rstrip('\n')
        print(f'Patched cell {i} (Seq2SeqTrainer)')
        patched += 1

if patched == 0:
    print('ERROR: No cells matched -- check cell IDs/indices.')
else:
    with open(NB_PATH, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f'\nSaved patched notebook ({patched} cells updated).')
