"""
DegreeDetailExtract — FastAPI backend v6.

Two-stage inference pipeline:
  Stage 1: Donut fine-tuned model → extracts structured field values
  Stage 2: Tesseract OCR + fuzzy matching → localises fields as pixel bounding boxes

The /extract endpoint returns:
  - fields: dict of extracted text values
  - missing_fields: list of fields not found
  - annotated_image: base64 PNG with coloured bounding box overlays drawn on the certificate

Tesseract is optional — if not installed the endpoint still works but returns no bbox.
Install: https://github.com/UB-Mannheim/tesseract/wiki (Windows) or `apt install tesseract-ocr`
"""

from __future__ import annotations

import base64
import io
import os
import re
import logging
from typing import Dict, List, Optional, Tuple

import sys
import os
import pathlib

# ── Resolve project root so we can import generator.date_utils ─────────────────
_BACKEND_DIR = pathlib.Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent.parent   # degree-extract-webapp/backend -> project root
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from generator.date_utils import normalize_date_to_ddmmyyyy as _normalize_date_shared
    _DATE_UTILS_AVAILABLE = True
except ImportError:
    _DATE_UTILS_AVAILABLE = False
    logger_pre = None

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from transformers import DonutProcessor, VisionEncoderDecoderModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("degree-extract-v6")

# ── Configuration ──────────────────────────────────────────────────────────────
MODEL_SOURCE = os.environ.get(
    "MODEL_SOURCE",
    r"v:\Vrushti\Projects\DegreeDetailExtract\checkpoints\best_model"
)
HF_TOKEN = os.environ.get("HF_TOKEN")

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

MAX_UPLOAD_MB = 15
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

FIELDS = [
    "student_name",
    "university_name",
    "course_name",
    "specialization",
    "pass_class",
    "authority_name",
    "issue_date",
]

# Colours for bounding box overlays (one per field)
FIELD_COLORS = {
    "student_name":    (52,  152, 219),   # blue
    "university_name": (155, 89,  182),   # purple
    "course_name":     (46,  204, 113),   # green
    "specialization":  (26,  188, 156),   # teal
    "pass_class":      (241, 196, 15),    # yellow
    "authority_name":  (230, 126, 34),    # orange
    "issue_date":      (231, 76,  60),    # red
}

FIELD_LABELS_DISPLAY = {
    "student_name":    "Student",
    "university_name": "University",
    "course_name":     "Course",
    "specialization":  "Specialization",
    "pass_class":      "Class",
    "authority_name":  "Authority",
    "issue_date":      "Date",
}

app = FastAPI(title="DegreeDetailExtract API v6", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ── Tesseract optional import ──────────────────────────────────────────────────
try:
    import pytesseract
    # On Windows: set path if tesseract not on PATH
    _tess_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(_tess_path):
        pytesseract.pytesseract.tesseract_cmd = _tess_path
    _TESSERACT_AVAILABLE = True
    logger.info("Tesseract available — bounding box localisation enabled.")
except ImportError:
    _TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not installed — bounding box localisation disabled.")

# ── Model loading ──────────────────────────────────────────────────────────────
device = "cuda" if torch.cuda.is_available() else "cpu"
processor: DonutProcessor | None = None
model: VisionEncoderDecoderModel | None = None


@app.on_event("startup")
def load_model() -> None:
    global processor, model
    logger.info("Loading model from %s on %s ...", MODEL_SOURCE, device)
    kwargs = {"token": HF_TOKEN} if HF_TOKEN else {}
    processor = DonutProcessor.from_pretrained(MODEL_SOURCE, **kwargs)
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_SOURCE, **kwargs).to(device)
    model.eval()
    logger.info("Model loaded successfully.")


# ── Field parsing ──────────────────────────────────────────────────────────────

def _strip_xml_tags(text: str) -> str:
    """Remove any leftover XML tags from a field value (safety cleanup)."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _normalize_date(raw: str) -> str:
    """
    Normalize extracted date to DD-MM-YYYY.
    v7: delegates to shared date_utils which handles written-out years.
    """
    if not raw or not raw.strip():
        return raw
    if _DATE_UTILS_AVAILABLE:
        return _normalize_date_shared(raw.strip())
    # Fallback if date_utils not importable
    from datetime import datetime
    raw = raw.strip()
    patterns = [
        "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d",
        "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y",
        "%B %Y", "%b. %Y", "%b %Y",
        "%d-%m-%y", "%d/%m/%y",
    ]
    for fmt in patterns:
        try:
            return datetime.strptime(raw, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    return raw


def _parse_fields(pred_str: str) -> Dict[str, str]:
    """Parse Donut output string, clean tags, normalize date."""
    result = {}
    for f in FIELDS:
        m = re.search(rf"<s_{f}>(.*?)</s_{f}>", pred_str, re.DOTALL)
        if m:
            val = _strip_xml_tags(m.group(1)).strip()
            if f == "issue_date":
                val = _normalize_date(val)
            result[f] = val
        else:
            result[f] = ""
    return result


# ── Donut inference ────────────────────────────────────────────────────────────

def _run_donut(img: Image.Image) -> Dict[str, str]:
    pixel_values = processor(images=img, return_tensors="pt").pixel_values.to(device)
    task_prompt = processor.tokenizer.decode(
        [model.config.decoder_start_token_id], skip_special_tokens=False
    )
    decoder_input_ids = processor.tokenizer(
        task_prompt, add_special_tokens=False, return_tensors="pt"
    ).input_ids.to(device)

    with torch.no_grad():
        outputs = model.generate(
            pixel_values=pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_new_tokens=256,       # v6: increased from 128 to avoid tag truncation
            early_stopping=True,
            no_repeat_ngram_size=3,   # v6: reduce repetition
            num_beams=4,              # v6: beam search for better output
        )
    pred_str = processor.tokenizer.decode(outputs[0], skip_special_tokens=False)
    logger.debug("Raw Donut output: %s", pred_str)
    return _parse_fields(pred_str)


# ── Tesseract OCR + bounding box localisation ──────────────────────────────────

def _preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """
    Preprocess certificate image for better Tesseract OCR accuracy on real photos.
    Steps: upscale to 300 DPI equivalent, convert to grayscale, denoise, binarize.
    """
    try:
        import numpy as np
        import cv2
        # 1. Upscale if small (Tesseract works best at 300 DPI / ~2000px height)
        w, h = img.size
        if h < 1800:
            scale = 1800 / h
            img = img.resize((int(w * scale), 1800), Image.LANCZOS)
        # 2. Convert to grayscale
        gray = np.array(img.convert("L"))
        # 3. Denoise
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
        # 4. Adaptive binarization (handles uneven lighting on certificate photos)
        binar = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
            blockSize=31, C=11
        )
        return Image.fromarray(binar).convert("RGB")
    except Exception as e:
        logger.warning("OCR preprocessing failed (%s), using original", e)
        return img


def _get_ocr_data(img: Image.Image) -> Optional[dict]:
    """Run Tesseract on image with preprocessing, return word-level data dict."""
    if not _TESSERACT_AVAILABLE:
        return None
    try:
        processed = _preprocess_for_ocr(img)
        # PSM 6 = assume uniform block of text (works best for certificates)
        custom_config = r"--oem 3 --psm 6 -l eng"
        data = pytesseract.image_to_data(
            processed,
            output_type=pytesseract.Output.DICT,
            config=custom_config
        )
        # Also scale bounding boxes back to original image coordinates
        scale_x = img.width / processed.width
        scale_y = img.height / processed.height
        if abs(scale_x - 1.0) > 0.05 or abs(scale_y - 1.0) > 0.05:
            data["left"]   = [int(x * scale_x) for x in data["left"]]
            data["top"]    = [int(y * scale_y) for y in data["top"]]
            data["width"]  = [int(w * scale_x) for w in data["width"]]
            data["height"] = [int(h * scale_y) for h in data["height"]]
        return data
    except Exception as e:
        logger.warning("Tesseract OCR failed: %s", e)
        return None


def _fuzzy_score(a: str, b: str) -> float:
    """Fuzzy similarity for matching extracted field values against OCR word spans."""
    a, b = a.lower().strip(), b.lower().strip()
    if not a or not b:
        return 0.0
    # Exact substring match: high confidence
    if a in b or b in a:
        return 0.95
    # Use rapidfuzz for better fuzzy matching if available
    try:
        from rapidfuzz import fuzz
        # Partial ratio works well when field value is a substring of the OCR span
        return max(
            fuzz.ratio(a, b) / 100.0,
            fuzz.partial_ratio(a, b) / 100.0,
            fuzz.token_sort_ratio(a, b) / 100.0,
        )
    except ImportError:
        pass
    # Fallback: trigram Jaccard
    def ngrams(s, n=3):
        return set(s[i:i+n] for i in range(len(s) - n + 1)) if len(s) >= n else {s}
    a_ng, b_ng = ngrams(a), ngrams(b)
    if not a_ng or not b_ng:
        return 0.0
    intersection = len(a_ng & b_ng)
    union = len(a_ng | b_ng)
    return intersection / union if union else 0.0


def _get_date_search_candidates(date_str: str) -> List[str]:
    """Generate potential surface text forms for OCR matching from a date string."""
    candidates = [date_str]
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", date_str)
    if m:
        d = int(m.group(1))
        month_num = int(m.group(2))
        y = m.group(3)
        months = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]
        if 1 <= month_num <= 12:
            m_name = months[month_num - 1]
            m_short = m_name[:3]
            candidates.extend([
                f"{d} {m_name} {y}",
                f"{d}th {m_name} {y}",
                f"{d}st {m_name} {y}",
                f"{d}nd {m_name} {y}",
                f"{d}rd {m_name} {y}",
                f"{m_name} {d} {y}",
                f"{m_name} {d}, {y}",
                f"{d} {m_short} {y}",
                f"{m_short} {d} {y}",
                f"{d:02d}/{month_num:02d}/{y}",
                f"{d:02d}-{month_num:02d}-{y}",
                f"{m_name} {y}",
                f"{m_name}",
            ])
            ord_words = {
                1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
                18: "eighteenth", 19: "nineteenth", 20: "twentieth", 21: "twenty first",
                24: "twenty fourth", 25: "twenty fifth", 29: "twenty ninth",
            }
            if d in ord_words:
                candidates.append(f"{ord_words[d]} day of {m_name}")
                candidates.append(f"{ord_words[d]} {m_name}")
    return candidates


def _find_field_boxes(
    fields: Dict[str, str],
    ocr_data: dict,
    img_w: int,
    img_h: int
) -> Dict[str, Optional[List[int]]]:
    """
    Match extracted field values against OCR word bounding boxes.
    Returns dict of field → [x, y, w, h] or None.
    """
    boxes: Dict[str, Optional[List[int]]] = {f: None for f in FIELDS}

    if ocr_data is None:
        return boxes

    n = len(ocr_data["text"])
    words = [
        {
            "text": ocr_data["text"][i].strip(),
            "left": ocr_data["left"][i],
            "top": ocr_data["top"][i],
            "width": ocr_data["width"][i],
            "height": ocr_data["height"][i],
            "conf": int(ocr_data["conf"][i]),
        }
        for i in range(n)
        if ocr_data["text"][i].strip() and int(ocr_data["conf"][i]) > 30
    ]

    for field_name, field_val in fields.items():
        if not field_val or len(field_val) < 2:
            continue

        search_targets = [field_val]
        if field_name == "issue_date":
            search_targets.extend(_get_date_search_candidates(field_val))

        best_score = 0.4  # minimum threshold
        best_span = None

        for target in search_targets:
            target_words = target.lower().split()
            max_window = min(len(target_words) + 3, 12)

            for window_size in range(1, max_window + 1):
                for start_idx in range(len(words) - window_size + 1):
                    span_words = words[start_idx:start_idx + window_size]
                    span_text = " ".join(w["text"] for w in span_words)
                    score = _fuzzy_score(target, span_text)
                    if score > best_score:
                        best_score = score
                        best_span = span_words

        if best_span:
            x1 = min(w["left"] for w in best_span)
            y1 = min(w["top"] for w in best_span)
            x2 = max(w["left"] + w["width"] for w in best_span)
            y2 = max(w["top"] + w["height"] for w in best_span)
            # Add small padding
            pad = 4
            x1 = max(0, x1 - pad)
            y1 = max(0, y1 - pad)
            x2 = min(img_w, x2 + pad)
            y2 = min(img_h, y2 + pad)
            boxes[field_name] = [x1, y1, x2 - x1, y2 - y1]

    return boxes


# ── Annotation rendering ────────────────────────────────────────────────────────

def _draw_boxes_on_image(
    img: Image.Image,
    fields: Dict[str, str],
    boxes: Dict[str, Optional[List[int]]]
) -> str:
    """
    Draw coloured bounding box overlays on the certificate image.
    Returns base64-encoded PNG string.
    """
    annotated = img.copy().convert("RGBA")
    overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    draw_main = ImageDraw.Draw(annotated)

    try:
        font = ImageFont.truetype("arial.ttf", max(12, img.height // 40))
    except Exception:
        font = ImageFont.load_default()

    for field_name in FIELDS:
        box = boxes.get(field_name)
        if box is None:
            continue

        x, y, w, h = box
        color_rgb = FIELD_COLORS.get(field_name, (255, 255, 255))
        color_rgba = (*color_rgb, 60)   # semi-transparent fill
        border_rgba = (*color_rgb, 200)

        # Semi-transparent fill
        draw_overlay.rectangle([x, y, x + w, y + h], fill=color_rgba)

        # Composite overlay
        annotated = Image.alpha_composite(annotated, overlay)
        overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)

        # Solid border
        draw_main = ImageDraw.Draw(annotated)
        draw_main.rectangle([x, y, x + w, y + h], outline=(*color_rgb, 255), width=2)

        # Label tag above the box
        label = FIELD_LABELS_DISPLAY.get(field_name, field_name)
        label_x = x
        label_y = max(0, y - 18)
        # Label background
        try:
            label_bbox = draw_main.textbbox((label_x, label_y), label, font=font)
            lw = label_bbox[2] - label_bbox[0] + 4
            lh = label_bbox[3] - label_bbox[1] + 2
        except Exception:
            lw, lh = len(label) * 7, 16
        draw_main.rectangle([label_x, label_y, label_x + lw, label_y + lh], fill=(*color_rgb, 220))
        draw_main.text((label_x + 2, label_y + 1), label, fill=(255, 255, 255, 255), font=font)

    # Convert to RGB PNG and base64-encode
    result_rgb = annotated.convert("RGB")
    buf = io.BytesIO()
    result_rgb.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "device": device,
        "tesseract_available": _TESSERACT_AVAILABLE,
        "version": "v6",
    }


@app.post("/extract")
async def extract(file: UploadFile = File(...)) -> dict:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. "
            f"Please upload a JPEG, PNG, or WebP image.",
        )

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_MB}MB.",
        )

    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=400,
            detail="Could not read this file as an image. Please upload a "
            "clear photo or scan of the certificate.",
        )

    if model is None or processor is None:
        raise HTTPException(status_code=503, detail="Model is still loading. Try again shortly.")

    try:
        # Stage 1: Donut extraction
        fields = _run_donut(img)
    except Exception:
        logger.exception("Donut inference failed")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while reading this certificate. Please try again.",
        )

    # Stage 2: Tesseract OCR + bounding box localisation
    annotated_image_b64 = None
    field_boxes: Dict[str, Optional[List[int]]] = {f: None for f in FIELDS}

    if _TESSERACT_AVAILABLE:
        try:
            ocr_data = _get_ocr_data(img)
            field_boxes = _find_field_boxes(fields, ocr_data, img.width, img.height)
            annotated_image_b64 = _draw_boxes_on_image(img, fields, field_boxes)
        except Exception:
            logger.exception("Bounding box annotation failed — returning fields without boxes")

    missing = [f for f in FIELDS if not fields.get(f)]

    return {
        "fields": fields,
        "missing_fields": missing,
        "field_boxes": field_boxes,
        "annotated_image": annotated_image_b64,  # base64 PNG or null
        "tesseract_available": _TESSERACT_AVAILABLE,
    }
