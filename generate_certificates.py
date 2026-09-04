#!/usr/bin/env python3
"""
Synthetic degree certificate generator — CLI entry point.

Generates N certificate images with full JSON ground-truth labels and
writes them to a HuggingFace-compatible imagefolder layout:

    <output_dir>/
        images/
            cert_00001.jpg
            cert_00002.jpg
            ...
        metadata_train.jsonl
        metadata_val.jsonl
        metadata_test.jsonl

Each JSONL line:
    {"file_name": "images/cert_00001.jpg", "student_name": "...", ...}

Usage examples
--------------
    python generate_certificates.py --count 5000 --output_dir ./dataset
    python generate_certificates.py --count 100  --output_dir ./dataset \\
        --no-augment --seed 42 --format png
    # Preview one certificate per template (15 images, no augment):
    python generate_certificates.py --count 15 --output_dir ./preview \\
        --no-augment --seed 0
"""

import argparse
import json
import random
import sys
from pathlib import Path

from tqdm import tqdm

from generator.faker_fields import generate_fields
from generator.renderer import render_certificate


# ── CLI argument parsing ───────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate synthetic degree certificate images.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--count",       type=int,   default=5000,
                   help="Total number of certificates to generate.")
    p.add_argument("--output_dir",  type=str,   default="./dataset",
                   help="Output directory for images and metadata files.")
    p.add_argument("--no-augment",  action="store_true",
                   help="Disable augmentation (useful for template debugging).")
    p.add_argument("--seed",        type=int,   default=None,
                   help="Random seed for reproducibility.")
    p.add_argument("--train_ratio", type=float, default=0.80,
                   help="Fraction allocated to the train split.")
    p.add_argument("--val_ratio",   type=float, default=0.10,
                   help="Fraction allocated to the val split (remainder → test).")
    p.add_argument("--format",      choices=["jpg", "png"], default="jpg",
                   help="Image format.")
    p.add_argument("--quality",     type=int,   default=92,
                   help="JPEG quality (ignored for PNG).")
    return p.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    output_dir = Path(args.output_dir)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    total   = args.count
    n_train = int(total * args.train_ratio)
    n_val   = int(total * args.val_ratio)
    n_test  = total - n_train - n_val

    # Pre-shuffle split assignments
    splits = ["train"] * n_train + ["val"] * n_val + ["test"] * n_test
    random.shuffle(splits)

    meta_files = {
        split: open(output_dir / f"metadata_{split}.jsonl", "w", encoding="utf-8")
        for split in ("train", "val", "test")
    }

    print(f"\n📄 Generating {total:,} certificates → {output_dir.resolve()}")
    print(f"   Train: {n_train:,}  |  Val: {n_val:,}  |  Test: {n_test:,}")
    print(f"   Augmentation: {'OFF' if args.no_augment else 'ON'}")
    if args.seed is not None:
        print(f"   Seed: {args.seed}")
    print()

    errors = 0
    for i in tqdm(range(total), desc="Generating", unit="cert"):
        cert_id = f"{i + 1:05d}"
        fname   = f"cert_{cert_id}.{args.format}"
        img_path = images_dir / fname

        try:
            fields = generate_fields()
            img    = render_certificate(fields, augment=not args.no_augment)

            save_kwargs: dict = {}
            if args.format == "jpg":
                save_kwargs = {"quality": args.quality, "optimize": True}
            img.convert("RGB").save(img_path, **save_kwargs)

            record = {"file_name": f"images/{fname}", **fields}
            meta_files[splits[i]].write(json.dumps(record, ensure_ascii=False) + "\n")

        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"\n[WARNING] cert #{cert_id} failed: {exc}", file=sys.stderr)

    for f in meta_files.values():
        f.close()

    ok = total - errors
    print(f"\n✅ Done.  Generated {ok:,}/{total:,} certificates.")
    if errors:
        print(f"   ⚠️  {errors} failures — see stderr for details.")
    print(f"   Dataset saved to: {output_dir.resolve()}\n")


if __name__ == "__main__":
    main()
