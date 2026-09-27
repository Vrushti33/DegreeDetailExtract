"""
DegreeDetailExtract — Local Training Script
GPU: NVIDIA RTX 4050 Laptop 6GB GDDR6
CPU: AMD R7 7735HS
RAM: 16GB

Setup:
    # 1. Install dependencies (run once in your conda/venv environment):
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
    pip install transformers>=4.37 datasets pillow faker tqdm
    pip install albumentations editdistance

    # 2. Install fonts (Windows — download manually):
    # Download Noto fonts from https://fonts.google.com/noto and place in:
    #   C:/Windows/Fonts/  (or use the FONT_DIR env var below)

Usage:
    python train_local.py --data_dir ./dataset_v5 --ckpt_dir ./checkpoints_v5
    python train_local.py --resume --data_dir ./dataset_v5 --ckpt_dir ./checkpoints_v5
    python train_local.py --data_dir ./dataset_v5 --generate  # also generate dataset first

RTX 4050 6GB memory budget:
    - Model weights (fp16): ~0.7 GB
    - Optimizer (fp32 master): ~1.4 GB
    - Activations @ batch=2 w/ grad checkpointing: ~2.5 GB
    - Total: ~4.6 GB — fits comfortably in 6 GB GDDR6

Epoch timing (RTX 4050):
    - 8,000 images × 87% train × 55% sampled = ~3,828 / batch 2 = ~1,914 batches
    - At ~1.5 batches/sec: ~21 min/epoch
    - 12 epochs = ~4.2 hours total (with early stopping, often fewer epochs)
"""

import os, sys, json, glob, shutil, argparse, gc, time
from pathlib import Path

import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import Dataset, DataLoader, RandomSampler
from torch.nn import CrossEntropyLoss
from tqdm import tqdm

from transformers import DonutProcessor, VisionEncoderDecoderModel, VisionEncoderDecoderConfig
from PIL import Image

# ── Config ────────────────────────────────────────────────────────────────────
REPO_DIR     = Path(__file__).parent           # root of DegreeDetailExtract repo
MODEL_NAME   = 'naver-clova-ix/donut-base'
FIELDS       = ['student_name', 'university_name', 'course_name',
                'specialization', 'pass_class', 'authority_name', 'issue_date']

# Training hyperparameters (same as Colab v5 — all anti-overfitting settings)
NUM_EPOCHS    = 12
LR            = 1.5e-5
LR_UNFREEZE   = 5e-6
WARMUP_STEPS  = 400
GRAD_ACCUM    = 2          # effective batch = 2 × 2 = 4 (same as Colab)
MAX_GRAD_NORM = 1.0
LABEL_SMOOTH  = 0.1
FREEZE_EPOCHS = 3
PATIENCE      = 3
EPOCH_FRAC    = 0.55

# RTX 4050 6GB: use batch=2 (not 4 like Colab T4 15GB)
BATCH         = 2
IMG_SIZE      = [960, 1280]   # height × width (same resolution as Colab)
LOG_EVERY     = 100


# ── Helpers ───────────────────────────────────────────────────────────────────

def build_target(row: dict) -> str:
    parts = ['<s_cert>']
    for f in FIELDS:
        parts.append(f'<s_{f}>{row.get(f, "")}</s_{f}>')
    parts.append('</s_cert>')
    return ''.join(parts)


class CertDataset(Dataset):
    def __init__(self, data_dir: str, split: str, processor):
        self.processor  = processor
        self.data_dir   = Path(data_dir)
        with open(self.data_dir / f'metadata_{split}.jsonl') as fp:
            self.rows = [json.loads(l) for l in fp]

    def __len__(self): return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        fpath = self.data_dir / row['file_name']
        try:
            img = Image.open(fpath).convert('RGB')
        except Exception:
            img = Image.new('RGB', (IMG_SIZE[1], IMG_SIZE[0]), (255, 255, 255))
        pv  = self.processor(images=img, return_tensors='pt').pixel_values.squeeze(0)
        tgt = build_target(row)
        lbl = self.processor.tokenizer(
            tgt, add_special_tokens=False,
            max_length=128, truncation=True, return_tensors='pt'
        ).input_ids.squeeze(0)
        return pv, lbl


def collate_fn(batch):
    pixels, labels_list = zip(*batch)
    pixels  = torch.stack(pixels)
    max_len = max(l.size(0) for l in labels_list)
    pad     = -100
    padded  = torch.full((len(labels_list), max_len), pad, dtype=torch.long)
    for i, l in enumerate(labels_list):
        padded[i, :l.size(0)] = l
    return pixels, padded


def compute_loss_smooth(logits, labels, smooth=LABEL_SMOOTH):
    vocab   = logits.size(-1)
    loss_fn = CrossEntropyLoss(label_smoothing=smooth, ignore_index=-100)
    return loss_fn(logits.view(-1, vocab), labels.view(-1))


def freeze_encoder(model):
    for name, param in model.named_parameters():
        if name.startswith('encoder.'):
            param.requires_grad = False
    frozen = sum(1 for n, p in model.named_parameters() if not p.requires_grad)
    total  = sum(1 for _ in model.parameters())
    print(f'  Encoder FROZEN: {frozen}/{total} params frozen')


def unfreeze_encoder(model, optimizer):
    for name, param in model.named_parameters():
        if name.startswith('encoder.'):
            param.requires_grad = True
    enc_params = [p for n, p in model.named_parameters()
                  if n.startswith('encoder.') and p.requires_grad]
    optimizer.add_param_group({'params': enc_params, 'lr': LR_UNFREEZE, 'weight_decay': 0.05})
    print(f'  Encoder UNFROZEN → added at lr={LR_UNFREEZE:.1e}')


def save_checkpoint(model, processor, optimizer, scheduler, ckpt_dir, epoch, val_loss, step, encoder_live):
    ep_dir = Path(ckpt_dir) / f'epoch_{epoch:02d}'
    ep_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(ep_dir)
    processor.save_pretrained(ep_dir)
    torch.save(optimizer.state_dict(), ep_dir / 'optimizer.pt')
    torch.save(scheduler.state_dict(), ep_dir / 'scheduler.pt')
    with open(ep_dir / 'train_meta.json', 'w') as fp:
        json.dump({'epoch': epoch, 'val_loss': val_loss,
                   'step': step, 'lr': max(pg['lr'] for pg in optimizer.param_groups),
                   'encoder_live': encoder_live}, fp, indent=2)
    print(f'  [ckpt] → {ep_dir}  (val_loss={val_loss:.4f})')
    # Prune optimizer states from older epochs (keep disk usage low)
    for d in sorted(Path(ckpt_dir).glob('epoch_*')):
        if d != ep_dir:
            for fname in ('optimizer.pt', 'scheduler.pt'):
                p = d / fname
                if p.exists(): p.unlink()


def get_lr(optimizer):
    return max(pg['lr'] for pg in optimizer.param_groups)


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_dataset(data_dir: str, n: int = 8000):
    """Generate synthetic dataset locally."""
    sys.path.insert(0, str(REPO_DIR))
    from generator.faker_fields import generate_fields
    from generator.renderer_v3 import render_certificate_v3, init_bg_pool

    data_path = Path(data_dir)
    (data_path / 'images').mkdir(parents=True, exist_ok=True)

    real_certs_dir = REPO_DIR / 'real_certs'
    n_bg = init_bg_pool(str(real_certs_dir)) if real_certs_dir.exists() else 0
    print(f'Loaded {n_bg} real backgrounds.')

    records, failed = [], 0
    for i in range(n):
        fields = generate_fields()
        try:
            img = render_certificate_v3(fields, augment=True)
        except Exception as e:
            failed += 1
            continue
        fname = f'images/cert_{i+1:05d}.jpg'
        img.save(data_path / fname, 'JPEG', quality=92)
        fields['file_name'] = fname
        records.append(fields)
        pct = 100.0 * (i + 1) / n
        print(f'  {i+1}/{n}  ({pct:.1f}%)  failed: {failed}', end='\r', flush=True)
    print()

    # Add real certs
    real_meta = real_certs_dir / 'metadata.jsonl'
    if real_meta.exists():
        with open(real_meta) as fp:
            real_rows = [json.loads(l) for l in fp]
        for row in real_rows:
            src = real_certs_dir / 'images' / row['file_name']
            if src.exists():
                dst = data_path / 'images' / f'real_{row["file_name"]}'
                shutil.copy2(src, dst)
                row['file_name'] = f'images/real_{row["file_name"]}'
                row['is_real']   = True
                records.append(row)
        print(f'  Added {len(real_rows)} real certificates.')

    import random
    random.shuffle(records)
    n_val  = max(10, int(len(records) * 0.08))
    n_test = max(10, int(len(records) * 0.05))
    splits = {
        'test':  records[:n_test],
        'val':   records[n_test:n_test + n_val],
        'train': records[n_test + n_val:],
    }
    for split, rows in splits.items():
        with open(data_path / f'metadata_{split}.jsonl', 'w') as fp:
            for row in rows:
                fp.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(f'Dataset ready: {len(splits["train"]):,} train | {len(splits["val"]):,} val | {len(splits["test"]):,} test')


def train(args):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'Device: {device}')
    if device == 'cuda':
        props = torch.cuda.get_device_properties(0)
        print(f'GPU: {props.name}  ({props.total_memory / 1024**3:.1f} GB VRAM)')

    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
    gc.collect()
    torch.cuda.empty_cache() if device == 'cuda' else None

    ckpt_dir = Path(args.ckpt_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # ── Load or resume model ──────────────────────────────────────────────────
    start_epoch   = 1
    step_global   = 0
    best_val_loss = float('inf')
    no_improve    = 0
    encoder_live  = False

    epoch_dirs = sorted(ckpt_dir.glob('epoch_*'))

    if args.resume and epoch_dirs:
        latest_dir = epoch_dirs[-1]
        print(f'Resuming from: {latest_dir}')
        with open(latest_dir / 'train_meta.json') as fp:
            meta = json.load(fp)
        start_epoch   = meta['epoch'] + 1
        step_global   = meta['step']
        best_val_loss = meta.get('val_loss', float('inf'))
        encoder_live  = meta.get('encoder_live', False)

        processor = DonutProcessor.from_pretrained(latest_dir)
        config    = VisionEncoderDecoderConfig.from_pretrained(latest_dir)
        config.encoder.image_size = IMG_SIZE
        config.use_cache = False
        model = VisionEncoderDecoderModel.from_pretrained(
            latest_dir, config=config, ignore_mismatched_sizes=True
        ).to(device)
    else:
        print(f'Loading base model: {MODEL_NAME}')
        processor = DonutProcessor.from_pretrained(MODEL_NAME)
        processor.image_processor.size = {'height': IMG_SIZE[0], 'width': IMG_SIZE[1]}
        processor.image_processor.do_align_long_axis = True

        config = VisionEncoderDecoderConfig.from_pretrained(MODEL_NAME)
        config.encoder.image_size = IMG_SIZE
        config.use_cache = False

        SPECIAL_TOKENS = (
            ['<s_cert>', '</s_cert>'] +
            [f'<s_{f}>' for f in FIELDS] +
            [f'</s_{f}>' for f in FIELDS]
        )
        processor.tokenizer.add_special_tokens({'additional_special_tokens': SPECIAL_TOKENS})

        model = VisionEncoderDecoderModel.from_pretrained(
            MODEL_NAME, config=config, ignore_mismatched_sizes=True
        )
        model.decoder.resize_token_embeddings(len(processor.tokenizer))
        model.config.decoder_start_token_id = processor.tokenizer.convert_tokens_to_ids(['<s_cert>'])[0]
        model.config.pad_token_id           = processor.tokenizer.pad_token_id
        model.config.eos_token_id           = processor.tokenizer.convert_tokens_to_ids(['</s_cert>'])[0]
        model = model.to(device)

    model.gradient_checkpointing_enable()
    model.config.use_cache = False
    n_params = sum(p.numel() for p in model.parameters()) / 1e6
    print(f'Model: {n_params:.0f}M params | {device} | IMG={IMG_SIZE}')

    # ── Freeze encoder if in early epochs ────────────────────────────────────
    if not encoder_live and start_epoch <= FREEZE_EPOCHS:
        freeze_encoder(model)

    # ── Dataset ───────────────────────────────────────────────────────────────
    train_ds = CertDataset(args.data_dir, 'train', processor)
    val_ds   = CertDataset(args.data_dir, 'val',   processor)

    epoch_samples = max(100, int(len(train_ds) * EPOCH_FRAC))
    print(f'Train: {len(train_ds):,} total | {epoch_samples:,}/epoch ({EPOCH_FRAC*100:.0f}%) | Val: {len(val_ds):,}')

    def make_train_dl():
        sampler = RandomSampler(train_ds, num_samples=epoch_samples, replacement=False)
        return DataLoader(train_ds, batch_size=BATCH, sampler=sampler,
                          num_workers=4, collate_fn=collate_fn, pin_memory=(device == 'cuda'))

    val_dl = DataLoader(val_ds, batch_size=BATCH, shuffle=False,
                        num_workers=4, collate_fn=collate_fn, pin_memory=(device == 'cuda'))

    # ── Optimizer ─────────────────────────────────────────────────────────────
    remaining   = NUM_EPOCHS - start_epoch + 1
    total_steps = (epoch_samples // BATCH) * remaining // GRAD_ACCUM

    optimizer = AdamW(filter(lambda p: p.requires_grad, model.parameters()),
                      lr=LR, weight_decay=0.05)
    scheduler = CosineAnnealingLR(optimizer, T_max=max(1, total_steps), eta_min=1e-7)
    scaler    = torch.cuda.amp.GradScaler() if device == 'cuda' else None

    if args.resume and epoch_dirs:
        latest_dir = epoch_dirs[-1]
        if (latest_dir / 'optimizer.pt').exists():
            try:
                optimizer.load_state_dict(torch.load(latest_dir / 'optimizer.pt', map_location=device))
                print('Optimizer restored.')
            except Exception: pass
        if (latest_dir / 'scheduler.pt').exists():
            try:
                scheduler.load_state_dict(torch.load(latest_dir / 'scheduler.pt', map_location=device))
                print('Scheduler restored.')
            except Exception: pass

    # ── Training loop ─────────────────────────────────────────────────────────
    print(f'\nTraining: epochs {start_epoch}-{NUM_EPOCHS} | batch={BATCH} | GradAccum={GRAD_ACCUM}')
    print(f'  LR={LR:.1e} | Warmup={WARMUP_STEPS} | LabelSmooth={LABEL_SMOOTH} | Patience={PATIENCE}\n')

    for epoch in range(start_epoch, NUM_EPOCHS + 1):
        # Unfreeze encoder at epoch FREEZE_EPOCHS+1
        if epoch == FREEZE_EPOCHS + 1 and not encoder_live:
            print(f'\n[Epoch {epoch}] Unfreezing encoder...')
            unfreeze_encoder(model, optimizer)
            encoder_live = True

        mode = '[encoder frozen]' if not encoder_live else '[full fine-tune]'
        print(f'\n=== Epoch {epoch}/{NUM_EPOCHS} {mode} ===')

        train_dl   = make_train_dl()
        model.train()
        train_loss = 0.0
        optimizer.zero_grad()
        t0 = time.time()

        for batch_idx, (pixels, labels) in enumerate(tqdm(train_dl, desc=f'  Epoch {epoch}', leave=False)):
            pixels = pixels.to(device)
            labels = labels.to(device)

            # Linear warmup
            if step_global < WARMUP_STEPS:
                for pg in optimizer.param_groups:
                    pg['lr'] = LR * step_global / max(1, WARMUP_STEPS)

            if device == 'cuda':
                with torch.amp.autocast('cuda'):
                    out  = model(pixel_values=pixels, labels=labels)
                    loss = compute_loss_smooth(out.logits, labels) / GRAD_ACCUM
                scaler.scale(loss).backward()
            else:
                out  = model(pixel_values=pixels, labels=labels)
                loss = compute_loss_smooth(out.logits, labels) / GRAD_ACCUM
                loss.backward()

            train_loss += loss.item() * GRAD_ACCUM

            if (batch_idx + 1) % GRAD_ACCUM == 0:
                if device == 'cuda':
                    scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)
                if device == 'cuda':
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    optimizer.step()
                if step_global >= WARMUP_STEPS:
                    scheduler.step()
                optimizer.zero_grad()
                step_global += 1

        avg_train = train_loss / len(train_dl)
        elapsed   = (time.time() - t0) / 60

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for pixels, labels in val_dl:
                pixels, labels = pixels.to(device), labels.to(device)
                if device == 'cuda':
                    with torch.amp.autocast('cuda'):
                        val_loss += model(pixel_values=pixels, labels=labels).loss.item()
                else:
                    val_loss += model(pixel_values=pixels, labels=labels).loss.item()
        val_loss /= len(val_dl)

        print(f'  Epoch {epoch}: train={avg_train:.4f} | val={val_loss:.4f} | {elapsed:.1f} min/epoch')
        save_checkpoint(model, processor, optimizer, scheduler,
                        args.ckpt_dir, epoch, val_loss, step_global, encoder_live)

        # Best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            no_improve    = 0
            best_dir = ckpt_dir / 'best'
            if best_dir.exists(): shutil.rmtree(best_dir)
            shutil.copytree(ckpt_dir / f'epoch_{epoch:02d}', best_dir)
            for fname in ('optimizer.pt', 'scheduler.pt'):
                p = best_dir / fname
                if p.exists(): p.unlink()
            print(f'  [best] val_loss={best_val_loss:.4f}')
        else:
            no_improve += 1
            if no_improve >= PATIENCE:
                print(f'  [early stop] No improvement for {PATIENCE} epochs. Stopping.')
                break

    print(f'\nTraining complete! Best val_loss={best_val_loss:.4f}')
    print(f'Load checkpoints_v5/best for inference.')


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DegreeDetailExtract local training (RTX 4050 6GB)')
    parser.add_argument('--data_dir',  default='./dataset_v5',    help='Path to dataset directory')
    parser.add_argument('--ckpt_dir',  default='./checkpoints_v5', help='Path to checkpoint directory')
    parser.add_argument('--resume',    action='store_true',         help='Resume from latest checkpoint')
    parser.add_argument('--generate',  action='store_true',         help='Generate dataset before training')
    parser.add_argument('--n',         type=int, default=8000,      help='Number of synthetic images to generate')
    args = parser.parse_args()

    if args.generate:
        print(f'Generating {args.n} synthetic certificates...')
        generate_dataset(args.data_dir, n=args.n)

    train(args)
