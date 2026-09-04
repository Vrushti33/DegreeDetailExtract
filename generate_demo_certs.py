"""
Generate a small set of test certificates for local demo.
Usage:
    python generate_demo_certs.py          # generates 10 certs
    python generate_demo_certs.py --n 20   # generates 20 certs

Output goes to:  demo_certs/images/
"""

import argparse, json, random
from pathlib import Path
from generator.renderer import render_certificate
from generator.faker_fields import generate_fields
from generator.augment import augment_image

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n",    type=int, default=10, help="Number of certificates")
    parser.add_argument("--out",  type=str, default="demo_certs", help="Output directory")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    out_dir = Path(args.out) / "images"
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for i in range(1, args.n + 1):
        fields = generate_fields()
        img    = render_certificate(fields)
        img    = augment_image(img)

        fname  = f"cert_{i:04d}.jpg"
        img.save(out_dir / fname, format="JPEG", quality=92)

        records.append({"file_name": f"images/{fname}", **fields})
        print(f"  [{i:3d}/{args.n}]  {fields['student_name'][:30]:<30}  "
              f"({fields['course_name'][:25]})")

    # Save metadata
    with open(Path(args.out) / "metadata.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n✅  {args.n} certificates saved to '{args.out}/images/'")
    print(f"    Metadata: '{args.out}/metadata.jsonl'")
    print(f"\nTo demo:\n  python app.py\n  Then upload any image from '{args.out}/images/'")

if __name__ == "__main__":
    main()
