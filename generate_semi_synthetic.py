#!/usr/bin/env python3
"""
Semi-Synthetic Certificate Generator
====================================
Generates high-fidelity semi-synthetic degree certificates using real certificate
scans/photos from `real_certs/` as authentic visual backdrops.

Key Workflow:
1. Inpaints and blanks the variable text areas (names, degrees, dates) from the real certificate
   while preserving the authentic paper texture, watermark, seals, crests, borders, and lighting.
2. Generates randomized realistic fields (student_name, university, degree, specialization,
   pass_class, authority, issue_date) using Faker and the project's curated vocabularies.
3. Dynamically typesets and renders the synthetic fields onto the real background with matching
   ink colors, appropriate typography, and automatic text wrapping.
4. Saves output images to `semi_synth_certs/images/` and outputs standard HuggingFace/Donut
   JSONL metadata with ground-truth XML task tokens.

Usage:
    python generate_semi_synthetic.py --count_per_cert 5
    python generate_semi_synthetic.py --total 50 --output_dir ./semi_synth_certs
"""

import os
import sys
import re
import json
import random
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from generator.faker_fields import generate_fields, PASS_CLASSES
from generator.fonts import _load
from generator.augment import augment_image


def get_font_custom(family: str, size: int, bold: bool = False, italic: bool = False) -> ImageFont.ImageFont:
    """Helper to load styled font via generator.fonts._load."""
    if family == "sans":
        style = "sans_bold" if bold else "sans_regular"
    elif family == "georgia":
        style = "georgia_bold" if bold else "georgia_regular"
    else:
        if bold:
            style = "serif_bold"
        elif italic:
            style = "serif_italic"
        else:
            style = "serif_regular"
    return _load(style, size)


# ── Inpainting & Template Preparation ──────────────────────────────────────────

def prepare_cleaned_template(
    pil_img: Image.Image,
    inpaint_radius: int = 3
) -> Tuple[Image.Image, Tuple[int, int, int], Dict[str, float]]:
    """
    Remove existing body text from a real certificate while preserving borders,
    ornate corners, seals, watermarks, and paper texture.

    Returns:
        (cleaned_pil_img, estimated_ink_color, layout_geometry)
    """
    img_rgb = np.array(pil_img.convert("RGB"))
    h, w = img_rgb.shape[:2]
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Adaptive threshold to isolate dark text strokes
    block_size = max(11, (min(w, h) // 40) | 1)  # must be odd
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, block_size, 7
    )

    # Define the body region to inpaint.
    # Keep borders (top 15%, bottom 18%, left 10%, right 10%) safe to protect seals & frames.
    body_y1 = int(h * 0.18)
    body_y2 = int(h * 0.82)
    body_x1 = int(w * 0.10)
    body_x2 = int(w * 0.90)

    # Sample text ink color from the text pixels inside the body region
    body_thresh = thresh[body_y1:body_y2, body_x1:body_x2]
    body_rgb = img_rgb[body_y1:body_y2, body_x1:body_x2]
    text_pixels = body_rgb[body_thresh > 0]

    if len(text_pixels) > 50:
        # 15th percentile of text pixels gives the dominant dark ink tone
        ink_r = int(np.percentile(text_pixels[:, 0], 25))
        ink_g = int(np.percentile(text_pixels[:, 1], 25))
        ink_b = int(np.percentile(text_pixels[:, 2], 25))
        # Ensure ink is sufficiently dark for legibility
        ink_color = (min(ink_r, 45), min(ink_g, 45), min(ink_b, 55))
    else:
        ink_color = (25, 25, 30)

    # Build inpainting mask for text in the body
    mask = np.zeros_like(thresh)
    mask[body_y1:body_y2, body_x1:body_x2] = thresh[body_y1:body_y2, body_x1:body_x2]

    # Dilate mask slightly so anti-aliased text boundaries are covered
    dilate_k = max(2, int(min(w, h) * 0.0025))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_k * 2 + 1, dilate_k * 2 + 1))
    mask_dilated = cv2.dilate(mask, kernel, iterations=1)

    # Inpaint using Telea fast marching method
    inpainted_bgr = cv2.inpaint(img_bgr, mask_dilated, inpaintRadius=inpaint_radius, flags=cv2.INPAINT_TELEA)
    inpainted_rgb = cv2.cvtColor(inpainted_bgr, cv2.COLOR_BGR2RGB)
    cleaned_pil = Image.fromarray(inpainted_rgb)

    geometry = {
        "x1": body_x1,
        "x2": body_x2,
        "y1": body_y1,
        "y2": body_y2,
        "width": w,
        "height": h,
    }

    return cleaned_pil, ink_color, geometry


# ── Text Rendering Helpers ─────────────────────────────────────────────────────

def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wrap text to fit within a given pixel width."""
    words = text.split()
    if not words:
        return [""]
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) <= max_width or not current_line:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))
    return lines


def render_centered_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    y: int,
    canvas_w: int,
    max_w: int,
    fill: Tuple[int, int, int],
    line_spacing: int = 4
) -> int:
    """Draw centered multi-line text and return next y coordinate."""
    lines = wrap_text(text, font, max_w, draw)
    curr_y = y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((canvas_w - tw) // 2, curr_y), line, font=font, fill=fill)
        curr_y += th + line_spacing
    return curr_y


# ── Semi-Synthetic Layout Engine ───────────────────────────────────────────────

CERT_LEAD_INS = [
    "This is to certify that",
    "It is hereby certified that",
    "The Senate of the University confers upon",
    "Having completed all academic requirements, the University certifies that",
    "Be it known that by authority of the Senate",
]

DEGREE_LEAD_INS = [
    "has been admitted to the Degree of",
    "is hereby awarded the Degree of",
    "has been conferred the Degree of",
    "having fulfilled all requirements is admitted to the Degree of",
]

def render_fields_onto_template(
    cleaned_bg: Image.Image,
    fields: Dict[str, str],
    geometry: Dict[str, float],
    ink_color: Tuple[int, int, int],
    font_family: str = "serif",
    lead_variant: int = 0
) -> Image.Image:
    """
    Renders the synthetic 7 fields onto the authentic certificate background.
    """
    img = cleaned_bg.copy()
    draw = ImageDraw.Draw(img)

    w = geometry["width"]
    h = geometry["height"]
    x1 = geometry["x1"]
    x2 = geometry["x2"]
    max_w = int(w * 0.76)

    # Scale font sizes proportionally to certificate height
    size_univ = max(16, int(h * 0.034))
    size_lead = max(11, int(h * 0.020))
    size_name = max(20, int(h * 0.042))
    size_deg  = max(16, int(h * 0.030))
    size_spec = max(13, int(h * 0.023))
    size_cls  = max(12, int(h * 0.021))
    size_bot  = max(11, int(h * 0.020))

    font_univ = get_font_custom(font_family, size_univ, bold=True)
    font_lead = get_font_custom(font_family, size_lead, italic=True)
    font_name = get_font_custom(font_family, size_name, bold=True)
    font_deg  = get_font_custom(font_family, size_deg, bold=True)
    font_spec = get_font_custom(font_family, size_spec)
    font_cls  = get_font_custom(font_family, size_cls, bold=True)
    font_bot  = get_font_custom(font_family, size_bot)

    # Pick phrasing
    cert_intro = CERT_LEAD_INS[lead_variant % len(CERT_LEAD_INS)]
    degree_intro = DEGREE_LEAD_INS[lead_variant % len(DEGREE_LEAD_INS)]

    # Dynamic vertical layout calculation
    start_y = int(h * 0.23)
    curr_y = start_y

    # 1. University Name (if prominent in text area)
    curr_y = render_centered_block(draw, fields["university_name"], font_univ, curr_y, w, max_w, ink_color)
    curr_y += int(h * 0.025)

    # 2. Certification Lead-in
    curr_y = render_centered_block(draw, cert_intro, font_lead, curr_y, w, max_w, ink_color)
    curr_y += int(h * 0.020)

    # 3. Student Name (Large, Bold, Prominent)
    curr_y = render_centered_block(draw, fields["student_name"], font_name, curr_y, w, max_w, ink_color)
    curr_y += int(h * 0.025)

    # 4. Degree Lead-in
    curr_y = render_centered_block(draw, degree_intro, font_lead, curr_y, w, max_w, ink_color)
    curr_y += int(h * 0.015)

    # 5. Course Name (Degree)
    curr_y = render_centered_block(draw, fields["course_name"], font_deg, curr_y, w, max_w, ink_color)
    curr_y += int(h * 0.012)

    # 6. Specialization
    if fields.get("specialization"):
        spec_text = f"in {fields['specialization']}"
        curr_y = render_centered_block(draw, spec_text, font_spec, curr_y, w, max_w, ink_color)
        curr_y += int(h * 0.016)

    # 7. Pass Class Award
    cls_text = f"Class Awarded: {fields['pass_class']}"
    curr_y = render_centered_block(draw, cls_text, font_cls, curr_y, w, max_w, ink_color)

    # 8. Bottom Row: Issue Date (left) and Authority Name (right)
    bot_y = int(h * 0.77)
    left_x = int(w * 0.12)
    right_x = int(w * 0.58)

    date_label = f"Date of Issue: {fields['issue_date']}"
    draw.text((left_x, bot_y), date_label, font=font_bot, fill=ink_color)

    # Authority may wrap if long
    auth_lines = wrap_text(fields["authority_name"], font_bot, int(w * 0.30), draw)
    ay = bot_y
    for aline in auth_lines:
        draw.text((right_x, ay), aline, font=font_bot, fill=ink_color)
        ay += size_bot + 2

    return img


# ── Master Dataset Generation Pipeline ─────────────────────────────────────────

def build_task_xml(fields: Dict[str, str]) -> str:
    """Formats 7 fields into Donut's target task XML string."""
    return (
        f"<s_cert>"
        f"<s_student_name>{fields['student_name']}</s_student_name>"
        f"<s_university_name>{fields['university_name']}</s_university_name>"
        f"<s_course_name>{fields['course_name']}</s_course_name>"
        f"<s_specialization>{fields['specialization']}</s_specialization>"
        f"<s_pass_class>{fields['pass_class']}</s_pass_class>"
        f"<s_authority_name>{fields['authority_name']}</s_authority_name>"
        f"<s_issue_date>{fields['issue_date']}</s_issue_date>"
        f"</s_cert>"
    )


def generate_semi_synthetic_dataset(
    real_certs_dir: Path,
    output_dir: Path,
    count_per_cert: int = 5,
    augment: bool = True,
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    seed: Optional[int] = 42
) -> None:
    """
    Main generator pipeline producing semi-synthetic certificate dataset.
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    real_files = sorted([
        f for f in real_certs_dir.iterdir()
        if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
    ])

    if not real_files:
        print(f"[ERROR] No image files found in {real_certs_dir.resolve()}")
        return

    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[INFO] Found {len(real_files)} real source certificates in: {real_certs_dir.name}/")
    print(f"       Generating {count_per_cert} semi-synthetic variations per certificate...")
    print(f"       Total target: {len(real_files) * count_per_cert} certificates")
    print(f"       Output folder: {output_dir.resolve()}\n")

    # Step 1: Pre-clean and cache the templates from real certificates
    print("[1/2] Inpainting and extracting templates from real certificates...")
    templates_cache = []
    for rf in tqdm(real_files, desc="Inpainting Real Certs"):
        try:
            with Image.open(rf) as im:
                cleaned_pil, ink_color, geom = prepare_cleaned_template(im)
                templates_cache.append({
                    "source_name": rf.name,
                    "cleaned_img": cleaned_pil,
                    "ink_color": ink_color,
                    "geometry": geom,
                })
        except Exception as e:
            print(f"   [WARN] Failed to process {rf.name}: {e}")

    if not templates_cache:
        print("[ERROR] Failed to create any templates from real certs.")
        return

    total_images = len(templates_cache) * count_per_cert
    n_train = int(total_images * train_ratio)
    n_val   = int(total_images * val_ratio)
    n_test  = total_images - n_train - n_val

    splits = ["train"] * n_train + ["val"] * n_val + ["test"] * n_test
    random.shuffle(splits)

    meta_files = {
        split: open(output_dir / f"metadata_{split}.jsonl", "w", encoding="utf-8")
        for split in ("train", "val", "test")
    }
    master_meta = open(output_dir / "metadata.jsonl", "w", encoding="utf-8")

    print(f"\n[2/2] Generating {total_images} semi-synthetic certificates...")
    print(f"      Splits: Train={n_train} | Val={n_val} | Test={n_test}")

    counter = 0
    font_choices = ["serif", "sans", "georgia"]

    for t_idx, t_data in enumerate(templates_cache):
        for v in range(count_per_cert):
            counter += 1
            cert_id = f"{counter:04d}"
            out_filename = f"semi_cert_{cert_id}.jpg"
            out_path = images_dir / out_filename

            fields = generate_fields()
            font_family = font_choices[v % len(font_choices)]

            rendered_img = render_fields_onto_template(
                cleaned_bg=t_data["cleaned_img"],
                fields=fields,
                geometry=t_data["geometry"],
                ink_color=t_data["ink_color"],
                font_family=font_family,
                lead_variant=v
            )

            # Optional subtle Albumentations augmentation
            if augment:
                rendered_img = augment_image(rendered_img)
            else:
                rendered_img = rendered_img.convert("RGB")

            # Save JPEG
            rendered_img.convert("RGB").save(out_path, quality=92, optimize=True)

            xml_ground_truth = build_task_xml(fields)

            record = {
                "file_name": f"images/{out_filename}",
                "source_real_cert": t_data["source_name"],
                **fields,
                "ground_truth": xml_ground_truth,
            }

            json_line = json.dumps(record, ensure_ascii=False) + "\n"
            master_meta.write(json_line)
            meta_files[splits[counter - 1]].write(json_line)

    for f in meta_files.values():
        f.close()
    master_meta.close()

    print(f"\n[OK] Successfully generated {counter} semi-synthetic certificates.")
    print(f"     Images:   {images_dir.resolve()}")
    print(f"     Metadata: {output_dir / 'metadata.jsonl'}")
    print(f"     Splits:   metadata_train.jsonl, metadata_val.jsonl, metadata_test.jsonl\n")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate semi-synthetic certificates from real scans in real_certs/"
    )
    parser.add_argument(
        "--real_dir", type=str, default="./real_certs",
        help="Path to folder containing real certificate images."
    )
    parser.add_argument(
        "--output_dir", type=str, default="./semi_synth_certs",
        help="Path to folder where semi-synthetic images and metadata will be saved."
    )
    parser.add_argument(
        "--count_per_cert", type=int, default=5,
        help="Number of synthetic variations to generate per real certificate."
    )
    parser.add_argument(
        "--no-augment", action="store_true",
        help="Disable Albumentations augmentations."
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed."
    )

    args = parser.parse_args()

    generate_semi_synthetic_dataset(
        real_certs_dir=Path(args.real_dir),
        output_dir=Path(args.output_dir),
        count_per_cert=args.count_per_cert,
        augment=not args.no_augment,
        seed=args.seed
    )


if __name__ == "__main__":
    main()
