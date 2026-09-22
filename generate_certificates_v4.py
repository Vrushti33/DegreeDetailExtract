#!/usr/bin/env python3
"""Generate synthetic certificate dataset for DegreeDetailExtract v4.

v4 improvements over v3 (in generator/faker_fields.py):
  - Open-vocabulary university names: 50% curated list, 50% procedurally
    generated (forces model to read pixels, not recall a memorised shortlist)
  - Varied authority_name formats: 6 different shapes (was always "Title, Name")
  - Expanded pass_class vocabulary: 20 values including Third Class, Division
    grades, Merit, Honours (were missing before and caused guaranteed failures
    on real certificates using those terms)
  - pass_class is absent ~30% of the time (matches real-world certificates)
  - Closing tags now consistently </s_field> matching registered special tokens

Usage (Colab / Linux):
    python generate_certificates_v4.py \\
        --count 5000 \\
        --output_dir /content/dataset_v4 \\
        --real_certs_dir /content/DegreeDetailExtract/real_certs \\
        --seed 42
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent))

from generator.faker_fields import generate_fields


def _try_load_renderer():
    """Return the best available renderer for the installed generator files."""
    for mod in ('generator.templates_v3', 'generator.templates_v2', 'generator.templates'):
        try:
            m = __import__(mod, fromlist=['render_certificate'])
            return m.render_certificate
        except (ImportError, AttributeError):
            continue
    raise ImportError("No render_certificate function found in generator/templates*.py")


def _try_load_augment():
    try:
        from generator.augment import augment_image
        return augment_image
    except ImportError:
        return lambda img: img   # no-op fallback


def _try_load_backgrounds(real_certs_dir):
    if not real_certs_dir or not Path(real_certs_dir).is_dir():
        return []
    try:
        from generator.realistic_bg import load_backgrounds
        pool = load_backgrounds(real_certs_dir)
        print(f"  Loaded {len(pool)} real certificate backgrounds.")
        return pool
    except Exception as e:
        print(f"  Warning: could not load real backgrounds ({e}); using plain backgrounds.")
        return []


def _try_get_font_dir():
    try:
        from generator.fonts import get_font_dir
        return get_font_dir()
    except Exception:
        return None


def generate(count, output_dir, real_certs_dir=None, seed=42, train_frac=0.87, val_frac=0.10):
    """Generate `count` synthetic v4 certificate images + JSONL metadata."""
    random.seed(seed)
    output_dir = Path(output_dir)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    render_certificate = _try_load_renderer()
    augment_image      = _try_load_augment()
    real_bg_pool       = _try_load_backgrounds(real_certs_dir)
    font_dir           = _try_get_font_dir()

    all_records = []
    failed      = 0
    print(f"Generating {count:,} v4 certificates -> {output_dir}")

    for i in range(count):
        fields = generate_fields()
        try:
            kwargs = {}
            if font_dir is not None:
                kwargs['font_dir'] = font_dir
            if real_bg_pool:
                kwargs['real_bg_pool'] = real_bg_pool
            img = render_certificate(fields, **kwargs)
            img = augment_image(img)
        except Exception as e:
            failed += 1
            if failed <= 5:
                print(f"  Warning: cert {i+1} failed to render ({e}); skipping.", file=sys.stderr)
            continue

        fname = f"images/cert_{i+1:05d}.jpg"
        img.save(output_dir / fname, "JPEG", quality=92)
        fields["file_name"] = fname
        all_records.append(fields)

        if (i + 1) % 500 == 0 or i + 1 == count:
            print(f"  {len(all_records):,}/{count:,}  (skipped: {failed})", end="\r", flush=True)

    print(f"\n  Generated {len(all_records):,} certificates  ({failed} skipped).")

    # Train / val / test split
    random.shuffle(all_records)
    n_train = int(len(all_records) * train_frac)
    n_val   = int(len(all_records) * val_frac)
    splits  = {
        "train": all_records[:n_train],
        "val":   all_records[n_train : n_train + n_val],
        "test":  all_records[n_train + n_val :],
    }

    for split, records in splits.items():
        out_path = output_dir / f"metadata_{split}.jsonl"
        with open(out_path, "w", encoding="utf-8") as fp:
            for rec in records:
                fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"  {split:5s}: {len(records):,} records -> {out_path.name}")

    print("Done.")
    return splits


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--count",          type=int, default=5000,          help="Number of certificates to generate")
    parser.add_argument("--output_dir",     type=str, default="./dataset_v4",help="Output directory")
    parser.add_argument("--real_certs_dir", type=str, default=None,          help="Directory of real certificate images for textures")
    parser.add_argument("--seed",           type=int, default=42,            help="Random seed")
    args = parser.parse_args()

    generate(
        count=args.count,
        output_dir=args.output_dir,
        real_certs_dir=args.real_certs_dir,
        seed=args.seed,
    )
