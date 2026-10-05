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
    Attempt to normalize any extracted date to DD-MM-YYYY.
    Returns raw value if normalization fails.
    """
    from datetime import datetime

    raw = raw.strip()
    if not raw:
        return raw

    patterns = [
        "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d",
        "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y",
        "%B %Y", "%b. %Y", "%b %Y",
        "%d-%m-%y", "%d/%m/%y",
    ]
    for fmt in patterns:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            continue

    # Ordinal pattern
    m = re.search(r"(\d+)(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(\w+),?\s+(\d{4})", raw, re.IGNORECASE)
    if m:
        day, month_str, year = m.group(1), m.group(2), m.group(3)
        for fmt in ["%d %B %Y", "%d %b %Y"]:
            try:
                from datetime import datetime as _dt
                dt = _dt.strptime(f"{day} {month_str} {year}", fmt)
                return dt.strftime("%d-%m-%Y")
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

def _get_ocr_data(img: Image.Image) -> Optional[dict]:
    """Run Tesseract on image, return word-level data dict."""
    if not _TESSERACT_AVAILABLE:
        return None
    try:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang="eng")
        return data
    except Exception as e:
        logger.warning("Tesseract OCR failed: %s", e)
        return None


def _fuzzy_score(a: str, b: str) -> float:
    """Simple character-level Jaccard similarity for fuzzy matching."""
    a, b = a.lower().strip(), b.lower().strip()
    if not a or not b:
        return 0.0
    # Try exact substring match first
    if a in b or b in a:
        return 1.0
    # N-gram overlap
    def ngrams(s, n=3):
        return set(s[i:i+n] for i in range(len(s) - n + 1)) if len(s) >= n else {s}
    a_ng, b_ng = ngrams(a), ngrams(b)
    if not a_ng or not b_ng:
        return 0.0
    intersection = len(a_ng & b_ng)
    union = len(a_ng | b_ng)
    return intersection / union if union else 0.0


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

        # Build sliding windows of 1–8 consecutive words
        best_score = 0.4  # minimum threshold
        best_span = None

        field_words = field_val.lower().split()
        max_window = min(len(field_words) + 3, 10)

        for window_size in range(1, max_window + 1):
            for start_idx in range(len(words) - window_size + 1):
                span_words = words[start_idx:start_idx + window_size]
                span_text = " ".join(w["text"] for w in span_words)
                score = _fuzzy_score(field_val, span_text)
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
