#!/usr/bin/env python3
"""
Realistic synthetic degree certificate generator (v3) — CLI entry point.

Generates 5,000–6,000 images using:
  - 36 certificate templates (22 original + 6 v2 + 8 new v3 prose styles)
  - Real paper textures from --real_certs_dir
  - Full ceremonial prose (16 style variants)
  - Rich date formats including ordinal textual dates
  - Optional pass_class (~30% of certs omit it)
  - Variable line spacing
  - Heavy augmentation (rotation, perspective, blur, noise)

Output layout (compatible with existing Donut trainer):
    <output_dir>/
        images/
            cert_00001.jpg
            ...
        metadata_train.jsonl
        metadata_val.jsonl
        metadata_test.jsonl

Usage
-----
    python generate_certificates_v3.py \\
        --count 5500 \\
        --output_dir ./dataset_v3 \\
        --real_certs_dir ./real_certs \\
        --seed 42

    # Preview only new v3 templates:
    python generate_certificates_v3.py \\
        --count 8 \\
        --output_dir ./preview_v3 \\
        --real_certs_dir ./real_certs \\
        --no-augment --only-v3 --seed 0
"""

import argparse
import json
import random
import sys
from pathlib import Path

from tqdm import tqdm

from generator.faker_fields import generate_fields
from generator.renderer_v3  import init_bg_pool, render_certificate_v3


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate v3 realistic synthetic degree certificate images.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--count",           type=int,   default=5500,
                   help="Total number of certificates to generate.")
    p.add_argument("--output_dir",      type=str,   default="./dataset_v3",
                   help="Output directory for images and metadata files.")
    p.add_argument("--real_certs_dir",  type=str,   default="./real_certs",
                   help="Directory with real certificate images for texture extraction.")
    p.add_argument("--no-augment",      action="store_true",
                   help="Disable augmentation (useful for previews).")
    p.add_argument("--only-v3",         action="store_true",
                   help="Only use the 8 new v3 templates.")
    p.add_argument("--only-new",        action="store_true",
                   help="Only use the 14 new templates (v2 + v3).")
    p.add_argument("--seed",            type=int,   default=None,
                   help="Random seed for reproducibility.")
    p.add_argument("--train_ratio",     type=float, default=0.80,
                   help="Fraction allocated to train split.")
    p.add_argument("--val_ratio",       type=float, default=0.10,
                   help="Fraction allocated to val split (remainder → test).")
    p.add_argument("--format",          choices=["jpg", "png"], default="jpg",
                   help="Image format.")
    p.add_argument("--quality",         type=int,   default=92,
                   help="JPEG quality (ignored for PNG).")
    return p.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    n_textures = init_bg_pool(args.real_certs_dir)
    if n_textures == 0:
        print(
            "[WARNING] No real certificate images found in "
            f"'{args.real_certs_dir}'. "
            "Texture templates will use flat colours.\n"
        )

    output_dir = Path(args.output_dir)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    total   = args.count
    n_train = int(total * args.train_ratio)
    n_val   = int(total * args.val_ratio)
    n_test  = total - n_train - n_val

    splits = ["train"] * n_train + ["val"] * n_val + ["test"] * n_test
    random.shuffle(splits)

    meta_files = {
        split: open(output_dir / f"metadata_{split}.jsonl", "w", encoding="utf-8")
        for split in ("train", "val", "test")
    }

    print(f"\nGenerating {total:,} v3 certificates -> {output_dir.resolve()}")
    print(f"   Train: {n_train:,}  |  Val: {n_val:,}  |  Test: {n_test:,}")
    print(f"   Real textures loaded : {n_textures}")
    print(f"   Augmentation         : {'OFF' if args.no_augment else 'ON (heavy)'}")
    if args.seed is not None:
        print(f"   Seed                 : {args.seed}")
    print()

    errors = 0
    for i in tqdm(range(total), desc="Generating", unit="cert"):
        cert_id  = f"{i + 1:05d}"
        fname    = f"cert_{cert_id}.{args.format}"
        img_path = images_dir / fname

        try:
            fields = generate_fields()
            img    = render_certificate_v3(
                fields,
                augment=not args.no_augment,
                only_v3=args.only_v3,
                only_new=args.only_new,
            )

            save_kwargs: dict = {}
            if args.format == "jpg":
                save_kwargs = {"quality": args.quality, "optimize": True}
            img.convert("RGB").save(img_path, **save_kwargs)

            record = {"file_name": f"images/{fname}", **fields}
            meta_files[splits[i]].write(json.dumps(record, ensure_ascii=False) + "\n")

        except Exception as exc:
            errors += 1
            print(f"\n[WARNING] cert #{cert_id} failed: {exc}", file=sys.stderr)

    for f in meta_files.values():
        f.close()

    ok = total - errors
    print(f"\nDone.  Generated {ok:,}/{total:,} v3 certificates.")
    if errors:
        print(f"   {errors} failures — check stderr for details.")
    print(f"   Dataset saved to: {output_dir.resolve()}\n")


if __name__ == "__main__":
    main()
