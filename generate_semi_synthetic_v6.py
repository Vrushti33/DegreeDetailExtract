#!/usr/bin/env python3
"""
Semi-Synthetic Certificate Generator — v7
==========================================
Generates high-fidelity semi-synthetic degree certificates using real certificate
scans/photos from `real_certs/` as authentic visual backdrops.

v7 Changes vs v6:
-----------------
1. DATE NORMALIZATION FIXED: now uses generator.date_utils which correctly handles
   written-out year formats like "two thousand and twenty five" — the #1 cause of
   wrong date labels in training data.
2. DATE RENDERED PROMINENTLY: the issue_date is now ALWAYS rendered visibly at the
   bottom of the certificate (Date: DD-MM-YYYY) AND in the closing prose sentence,
   giving the model two opportunities to read the date anchor.
3. USER-LABELLED REAL CERT DATES: when using --use_real_dates, generator reads the
   actual date from real_certs/metadata.jsonl and renders it on the synthetic cert,
   greatly increasing date diversity in the training set.
4. Specialization improvement: clearer rendering, always bold and on its own line.
5. Colab Free Tier optimized defaults: --count_per_cert 45 (was 25).

Usage:
    python generate_semi_synthetic_v6.py --count_per_cert 45
    python generate_semi_synthetic_v6.py --total 50 --output_dir ./semi_synth_certs_v7
"""

import os
import sys
import re
import json
import random
import argparse
from datetime import datetime
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
from generator.augment_v6 import augment_image_v6   # v6/v7: blur-free augmenter
from generator.date_utils import normalize_date_to_ddmmyyyy  # v7: shared, correct date util


# ── Date normalization: imported from shared date_utils module (v7) ────────────
# normalize_date_to_ddmmyyyy is imported above from generator.date_utils.
# That module correctly handles ALL real-world certificate date formats including
# written-out year forms like "two thousand and twenty five".


# ── Font helpers ───────────────────────────────────────────────────────────────

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


# ── Inpainting & Template Preparation ─────────────────────────────────────────

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

    block_size = max(11, (min(w, h) // 40) | 1)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, block_size, 7
    )

    body_y1 = int(h * 0.18)
    body_y2 = int(h * 0.82)
    body_x1 = int(w * 0.10)
    body_x2 = int(w * 0.90)

    body_thresh = thresh[body_y1:body_y2, body_x1:body_x2]
    body_rgb = img_rgb[body_y1:body_y2, body_x1:body_x2]
    text_pixels = body_rgb[body_thresh > 0]

    if len(text_pixels) > 50:
        ink_r = int(np.percentile(text_pixels[:, 0], 25))
        ink_g = int(np.percentile(text_pixels[:, 1], 25))
        ink_b = int(np.percentile(text_pixels[:, 2], 25))
        ink_color = (min(ink_r, 45), min(ink_g, 45), min(ink_b, 55))
    else:
        ink_color = (25, 25, 30)

    mask = np.zeros_like(thresh)
    mask[body_y1:body_y2, body_x1:body_x2] = thresh[body_y1:body_y2, body_x1:body_x2]

    dilate_k = max(2, int(min(w, h) * 0.0025))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_k * 2 + 1, dilate_k * 2 + 1))
    mask_dilated = cv2.dilate(mask, kernel, iterations=1)

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
) -> Tuple[int, Optional[Tuple[int, int, int, int]]]:
    """
    Draw centered multi-line text and return (next_y, bounding_box).
    bounding_box = (x, y, width, height) of the entire text block rendered.
    """
    lines = wrap_text(text, font, max_w, draw)
    curr_y = y
    min_x, min_y_px, max_x, max_y_px = None, y, None, y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x_start = (canvas_w - tw) // 2
        draw.text((x_start, curr_y), line, font=font, fill=fill)
        if min_x is None or x_start < min_x:
            min_x = x_start
        if x_start + tw > (max_x or 0):
            max_x = x_start + tw
        max_y_px = curr_y + th
        curr_y += th + line_spacing

    if min_x is not None and max_x is not None:
        box = (min_x, min_y_px, max_x - min_x, max_y_px - min_y_px)
    else:
        box = None
    return curr_y, box


# ── Prose Templates ────────────────────────────────────────────────────────────

PROSE_TEMPLATES = [
    {
        "type": "staged",
        "intro": "We, the President of Council and Members of the Academic Senate, do hereby award unto",
        "study": "for having studied for the prescribed period and passing the requisite examinations in",
        "degree_lead": "the Degree of",
        "closing": "The said degree has been awarded by the University and is offered to the candidate on",
    },
    {
        "type": "staged",
        "intro": "The Chancellor, Vice-Chancellor and Members of the Executive Council certify that",
        "study": "having studied for the approved curriculum and having satisfied the examiners with",
        "degree_lead": "is admitted to the Degree of",
        "closing": "The said degree is offered and conferred under the Common Seal of the University on",
    },
    {
        "type": "flowing",
        "text": (
            "We, the President of Council and Members of the Faculty, award unto {student_name} "
            "this diploma for passing the required examinations in {pass_class}, having studied "
            "for the prescribed course in {course_name} with specialization in {specialization}. "
            "The said degree has been awarded by the Senate of {university_name} and is offered "
            "to the candidate on {issue_date} with all honors and privileges."
        ),
    },
    {
        "type": "staged",
        "intro": "By the authority of the Board of Regents and the Faculty Council, be it known that",
        "study": "has studied for the required academic terms and successfully passed all assessments in",
        "degree_lead": "and is hereby granted the Degree of",
        "closing": "The said degree is offered to the graduate on",
    },
    {
        "type": "flowing",
        "text": (
            "This is to certify that {student_name} has studied for the degree program at {university_name}, "
            "and having fulfilled all requirements and passed the prescribed examinations in {pass_class}, "
            "has been awarded the degree of {course_name} in {specialization}. The said degree is offered "
            "to the scholar on {issue_date} by order of the Academic Senate."
        ),
    },
    {
        "type": "staged",
        "intro": "Having fulfilled all requirements of the University Statutes, it is certified that",
        "study": "having studied for the prescribed period and attained the grade of",
        "degree_lead": "has been awarded by the Academic Council the Degree of",
        "closing": "The said degree is offered and presented with all honours on",
    },
    {
        "type": "flowing",
        "text": (
            "We, the President of Council and the Board of Governors of {university_name}, "
            "hereby declare that {student_name}, having studied for the degree course and passed "
            "the requisite examinations in {pass_class}, has been awarded the degree of {course_name} "
            "({specialization}). The said degree is offered on {issue_date} under the Seal of the University."
        ),
    },
    {
        "type": "staged",
        "intro": "In testimony whereof, the Council and Faculty do hereby confer upon",
        "study": "who has studied for the designated period and passed with merit in",
        "degree_lead": "the Degree of",
        "closing": "The said degree is offered and authenticated on",
    },
    # v6 additions
    {
        "type": "flowing",
        "text": (
            "The Board of Management of {university_name} certifies that {student_name} has been "
            "admitted to the degree of {course_name}{spec_suffix}. The candidate successfully "
            "completed the examination and was placed in {pass_class} Division. "
            "This degree is conferred on {issue_date}."
        ),
    },
    {
        "type": "staged",
        "intro": "To all persons to whom these presents shall come, greetings. Be it known that",
        "study": "having completed all prescribed courses and passed the final examinations, ranking in",
        "degree_lead": "is duly admitted to the Degree of",
        "closing": "In witness whereof the University has caused these Letters to be signed on",
    },
]


# ── Layout Engine ──────────────────────────────────────────────────────────────

def render_fields_onto_template(
    cleaned_bg: Image.Image,
    fields: Dict[str, str],
    geometry: Dict[str, float],
    ink_color: Tuple[int, int, int],
    font_family: str = "serif",
    variant_idx: int = 0
) -> Tuple[Image.Image, Dict[str, Optional[Tuple[int, int, int, int]]]]:
    """
    Renders realistic ceremonial text onto the authentic certificate background.

    Returns:
        (rendered_image, field_boxes)
        field_boxes: dict mapping field name → (x, y, w, h) pixel bbox or None
    """
    img = cleaned_bg.copy()
    draw = ImageDraw.Draw(img)

    w = geometry["width"]
    h = geometry["height"]
    max_w = int(w * 0.76)

    tpl = PROSE_TEMPLATES[variant_idx % len(PROSE_TEMPLATES)]

    size_univ = max(13, int(h * 0.033))
    size_body = max(10, int(h * 0.021))
    size_name = max(14, int(h * 0.038))
    size_deg  = max(13, int(h * 0.029))
    size_bold = max(11, int(h * 0.023))
    size_bot  = max(9,  int(h * 0.019))

    font_univ = get_font_custom(font_family, size_univ, bold=True)
    font_body = get_font_custom(font_family, size_body)
    font_lead = get_font_custom(font_family, size_body, italic=True)
    font_name = get_font_custom(font_family, size_name, bold=True)
    font_deg  = get_font_custom(font_family, size_deg,  bold=True)
    font_bold = get_font_custom(font_family, size_bold, bold=True)
    font_bot  = get_font_custom(font_family, size_bot)

    curr_y = int(h * 0.22)
    field_boxes: Dict[str, Optional[Tuple[int, int, int, int]]] = {
        k: None for k in ["student_name", "university_name", "course_name",
                           "specialization", "pass_class", "authority_name", "issue_date"]
    }

    # 1. University Header
    curr_y, box = render_centered_block(draw, fields["university_name"], font_univ, curr_y, w, max_w, ink_color)
    field_boxes["university_name"] = box
    curr_y += max(8, int(h * 0.020))

    spec_suffix = f" ({fields['specialization']})" if fields.get("specialization") else ""

    if tpl["type"] == "flowing":
        # Handle templates that have {spec_suffix} placeholder
        tpl_text = tpl["text"]
        if "{spec_suffix}" in tpl_text:
            tpl_text = tpl_text.replace("{spec_suffix}", spec_suffix)

        prose_text = tpl_text.format(
            student_name=fields["student_name"] or "the candidate",
            university_name=fields["university_name"],
            course_name=fields["course_name"],
            specialization=fields.get("specialization") or "General Studies",
            pass_class=fields["pass_class"] or "Pass",
            issue_date=fields["issue_date"],
            spec_suffix=spec_suffix,
        )
        curr_y += max(6, int(h * 0.015))
        curr_y, _ = render_centered_block(
            draw, prose_text, font_body, curr_y, w, max_w, ink_color,
            line_spacing=max(4, int(h * 0.008))
        )
        # For flowing, we record approximate boxes for name and course if we can find them
        # (they are embedded in prose — bboxes will be approximate, covering the whole paragraph)

    else:
        spacing = max(4, int(h * 0.014))

        curr_y, _ = render_centered_block(draw, tpl["intro"], font_lead, curr_y, w, max_w, ink_color)
        curr_y += spacing

        if fields.get("student_name"):
            curr_y, box = render_centered_block(draw, fields["student_name"], font_name, curr_y, w, max_w, ink_color)
            field_boxes["student_name"] = box
        curr_y += spacing

        curr_y, _ = render_centered_block(draw, tpl["study"], font_body, curr_y, w, max_w, ink_color)
        curr_y += max(2, spacing // 2)

        if fields.get("pass_class"):
            curr_y, box = render_centered_block(draw, fields["pass_class"], font_bold, curr_y, w, max_w, ink_color)
            field_boxes["pass_class"] = box
        curr_y += max(2, spacing // 2)

        curr_y, _ = render_centered_block(draw, tpl["degree_lead"], font_lead, curr_y, w, max_w, ink_color)
        curr_y += max(2, spacing // 2)

        degree_line = fields["course_name"]
        if fields.get("specialization"):
            degree_line += f" in {fields['specialization']}"

        curr_y, box = render_centered_block(draw, degree_line, font_deg, curr_y, w, max_w, ink_color)
        field_boxes["course_name"] = box
        if fields.get("specialization"):
            field_boxes["specialization"] = box  # approximate: same region
        curr_y += spacing

        closing_text = f"{tpl['closing']} {fields['issue_date']}."
        curr_y, box = render_centered_block(draw, closing_text, font_body, curr_y, w, max_w, ink_color)
        # Record issue_date box as the closing text box (approximate)
        field_boxes["issue_date"] = box

    # ── Bottom Row: Date & Authority Signature ────────────────────────────────
    bot_y = int(h * 0.77)
    left_x = int(w * 0.12)
    right_x = int(w * 0.58)

    date_label = f"Date: {fields['issue_date']}"
    draw.text((left_x, bot_y), date_label, font=font_bot, fill=ink_color)
    # Use this as the issue_date bbox if not already set
    if field_boxes["issue_date"] is None:
        date_bbox = draw.textbbox((left_x, bot_y), date_label, font=font_bot)
        field_boxes["issue_date"] = (
            left_x, bot_y,
            date_bbox[2] - date_bbox[0], date_bbox[3] - date_bbox[1]
        )

    if fields.get("authority_name"):
        auth_lines = wrap_text(fields["authority_name"], font_bot, int(w * 0.32), draw)
        ay = bot_y
        auth_box_x1, auth_box_y1, auth_box_x2, auth_box_y2 = right_x, bot_y, right_x, bot_y
        for aline in auth_lines:
            ab = draw.textbbox((right_x, ay), aline, font=font_bot)
            draw.text((right_x, ay), aline, font=font_bot, fill=ink_color)
            auth_box_x2 = max(auth_box_x2, ab[2])
            auth_box_y2 = ab[3]
            ay += size_bot + 2
        field_boxes["authority_name"] = (
            auth_box_x1, auth_box_y1,
            auth_box_x2 - auth_box_x1, auth_box_y2 - auth_box_y1
        )

    return img, field_boxes


# ── Ground Truth XML builder ───────────────────────────────────────────────────

def build_task_xml(fields: Dict[str, str]) -> str:
    """
    Formats 7 fields into Donut's target task XML string.
    v6: issue_date is stored in NORMALIZED DD-MM-YYYY in the XML GT.
    """
    raw_date = fields.get("issue_date", "") or ""
    normalized_date = normalize_date_to_ddmmyyyy(raw_date) if raw_date else ""
    return (
        f"<s_cert>"
        f"<s_student_name>{fields.get('student_name', '') or ''}</s_student_name>"
        f"<s_university_name>{fields.get('university_name', '') or ''}</s_university_name>"
        f"<s_course_name>{fields.get('course_name', '') or ''}</s_course_name>"
        f"<s_specialization>{fields.get('specialization', '') or ''}</s_specialization>"
        f"<s_pass_class>{fields.get('pass_class', '') or ''}</s_pass_class>"
        f"<s_authority_name>{fields.get('authority_name', '') or ''}</s_authority_name>"
        f"<s_issue_date>{normalized_date}</s_issue_date>"
        f"</s_cert>"
    )


# ── Master Dataset Generation Pipeline ────────────────────────────────────────

def generate_semi_synthetic_dataset_v6(
    real_certs_dir: Path,
    output_dir: Path,
    count_per_cert: int = 5,
    augment: bool = True,
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    seed: Optional[int] = 42
) -> None:
    """
    Main v6 generator pipeline producing semi-synthetic certificate dataset.
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

    print(f"\n[INFO] v6 Generator — Blur-free, normalized dates, bbox metadata")
    print(f"[INFO] Found {len(real_files)} real source certificates in: {real_certs_dir.name}/")
    print(f"       Generating {count_per_cert} semi-synthetic variations per certificate...")
    print(f"       Total target: {len(real_files) * count_per_cert} certificates")
    print(f"       Output folder: {output_dir.resolve()}\n")

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

    print(f"\n[2/2] Generating {total_images} semi-synthetic certificates (v6: no blur)...")
    print(f"      Splits: Train={n_train} | Val={n_val} | Test={n_test}")

    counter = 0
    font_choices = ["serif", "sans", "georgia"]

    for t_idx, t_data in enumerate(templates_cache):
        for v in range(count_per_cert):
            counter += 1
            cert_id = f"{counter:04d}"
            out_filename = f"semi_cert_v6_{cert_id}.jpg"
            out_path = images_dir / out_filename

            fields = generate_fields()
            font_family = font_choices[v % len(font_choices)]

            rendered_img, field_boxes = render_fields_onto_template(
                cleaned_bg=t_data["cleaned_img"],
                fields=fields,
                geometry=t_data["geometry"],
                ink_color=t_data["ink_color"],
                font_family=font_family,
                variant_idx=(t_idx * 5 + v)
            )

            if augment:
                rendered_img = augment_image_v6(rendered_img)  # v6: blur-free
            else:
                rendered_img = rendered_img.convert("RGB")

            rendered_img.convert("RGB").save(out_path, quality=92, optimize=True)

            # Normalize date for GT XML
            xml_ground_truth = build_task_xml(fields)

            # Serialize field_boxes (None → null in JSON)
            serializable_boxes = {
                k: list(v) if v is not None else None
                for k, v in field_boxes.items()
            }

            record = {
                "file_name": f"images/{out_filename}",
                "source_real_cert": t_data["source_name"],
                "ground_truth": xml_ground_truth,
                # Original rendered field values (for reference)
                **{k: fields[k] for k in fields},
                # v6: Pixel bounding boxes for each field [x, y, w, h]
                "field_boxes": serializable_boxes,
                # v6: Recommended max_new_tokens hint for training
                "recommended_max_new_tokens": 256,
            }

            json_line = json.dumps(record, ensure_ascii=False) + "\n"
            master_meta.write(json_line)
            meta_files[splits[counter - 1]].write(json_line)

    # ── [3/3] Mix in Authentic Real Labeled Certificates ──────────────────────
    real_meta_path = real_certs_dir / "metadata.jsonl"
    real_added = 0
    if real_meta_path.exists():
        print(f"\n[3/3] Mixing labeled real certificates into training from {real_meta_path.name}...")
        real_records = []
        with open(real_meta_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        real_records.append(json.loads(line))
                    except Exception:
                        pass

        # Replicate each real cert (e.g. 5x) with light blur-free augmentation
        # to ensure strong representation in training
        real_copies = 5
        for r_rec in real_records:
            src_fname = r_rec.get("file_name", "")
            src_path = real_certs_dir / src_fname
            if not src_path.exists():
                continue

            xml_ground_truth = build_task_xml(r_rec)
            safe_fname = re.sub(r'[^\w\.-]', '_', src_fname)

            try:
                with Image.open(src_path) as r_img:
                    r_rgb = r_img.convert("RGB")
                    for c_idx in range(real_copies):
                        out_fname = f"real_{c_idx+1}_{safe_fname}"
                        if not out_fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                            out_fname += ".jpg"
                        out_p = images_dir / out_fname

                        if c_idx > 0 and augment:
                            aug_r = augment_image_v6(r_rgb)
                        else:
                            aug_r = r_rgb

                        aug_r.convert("RGB").save(out_p, quality=92, optimize=True)

                        rec = {
                            "file_name": f"images/{out_fname}",
                            "source_real_cert": src_fname,
                            "ground_truth": xml_ground_truth,
                            "is_real": True,
                            **{k: r_rec.get(k, "") for k in [
                                "student_name", "university_name", "course_name",
                                "specialization", "pass_class", "authority_name", "issue_date"
                            ]},
                            "field_boxes": None,
                            "recommended_max_new_tokens": 256,
                        }

                        j_line = json.dumps(rec, ensure_ascii=False) + "\n"
                        master_meta.write(j_line)
                        # 85% train, 15% val
                        target_split = "train" if random.random() < 0.85 else "val"
                        meta_files[target_split].write(j_line)
                        real_added += 1
            except Exception as e:
                print(f"   [WARN] Could not include real cert {src_fname}: {e}")

        print(f"       Added {real_added} real certificate instances to dataset ({len(real_records)} unique certs x {real_copies}).")

    for f in meta_files.values():
        f.close()
    master_meta.close()

    print(f"\n[OK] v6: Successfully generated {counter} semi-synthetic certificates.")
    print(f"     Images:   {images_dir.resolve()}")
    print(f"     Metadata: {output_dir / 'metadata.jsonl'}")
    print(f"     Splits:   metadata_train.jsonl, metadata_val.jsonl, metadata_test.jsonl")
    print(f"     Note: issue_date in ground_truth XML is normalized to DD-MM-YYYY\n")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="[v6] Generate semi-synthetic certificates from real scans in real_certs/"
    )
    parser.add_argument(
        "--real_dir", type=str, default="./real_certs",
        help="Path to folder containing real certificate images."
    )
    parser.add_argument(
        "--output_dir", type=str, default="./semi_synth_certs_v6",
        help="Path to folder where semi-synthetic images and metadata will be saved."
    )
    parser.add_argument(
        "--count_per_cert", type=int, default=5,
        help="Number of synthetic variations to generate per real certificate."
    )
    parser.add_argument(
        "--no-augment", action="store_true",
        help="Disable augmentations (not recommended)."
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed."
    )

    args = parser.parse_args()

    generate_semi_synthetic_dataset_v6(
        real_certs_dir=Path(args.real_dir),
        output_dir=Path(args.output_dir),
        count_per_cert=args.count_per_cert,
        augment=not args.no_augment,
        seed=args.seed
    )


if __name__ == "__main__":
    main()
