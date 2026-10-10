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

def _get_ocr_words(img: Image.Image) -> List[dict]:
    """
    Extract word-level OCR tokens with coordinates scaled to original image dimensions.
    Uses dual-pass strategy:
      - Pass 1: PSM 3 for connected multi-line reading order and ceremonial prose.
      - Pass 2: PSM 11 for sparse, isolated text blocks (labels, dates, division stamps).
    """
    if not _TESSERACT_AVAILABLE:
        return []

    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
        w, h = img.size
        scale = 1.0

        if h < 1600:
            scale = 1600.0 / h
            img_ocr = img.resize((int(w * scale), 1600), Image.LANCZOS)
        elif h > 2400:
            scale = 2400.0 / h
            img_ocr = img.resize((int(w * scale), 2400), Image.LANCZOS)
        else:
            img_ocr = img

        inv_scale = 1.0 / scale

        # Pass 1: PSM 3 (standard layout & reading order)
        d3 = pytesseract.image_to_data(
            img_ocr,
            output_type=pytesseract.Output.DICT,
            config=r"--oem 3 --psm 3 -l eng"
        )
        words = []
        for i in range(len(d3["text"])):
            t = d3["text"][i].strip()
            clean = re.sub(r"[^\w]", "", t).lower()
            if clean:
                words.append({
                    "raw": t,
                    "clean": clean,
                    "left": int(d3["left"][i] * inv_scale),
                    "top": int(d3["top"][i] * inv_scale),
                    "width": int(d3["width"][i] * inv_scale),
                    "height": int(d3["height"][i] * inv_scale),
                    "conf": int(d3["conf"][i]) if "conf" in d3 else 50,
                })

        # Pass 2: PSM 11 (sparse text, captures isolated labels and values missed by PSM 3)
        d11 = pytesseract.image_to_data(
            img_ocr,
            output_type=pytesseract.Output.DICT,
            config=r"--oem 3 --psm 11 -l eng"
        )
        for i in range(len(d11["text"])):
            t = d11["text"][i].strip()
            clean = re.sub(r"[^\w]", "", t).lower()
            if not clean:
                continue
            l11 = int(d11["left"][i] * inv_scale)
            t11 = int(d11["top"][i] * inv_scale)
            w11 = int(d11["width"][i] * inv_scale)
            h11 = int(d11["height"][i] * inv_scale)

            # Avoid duplicates if center already covered by a Pass 1 word
            cx, cy = l11 + w11 / 2, t11 + h11 / 2
            overlap = any(
                (w["left"] <= cx <= w["left"] + w["width"] and
                 w["top"] - 10 <= cy <= w["top"] + w["height"] + 10)
                for w in words
            )
            if not overlap:
                words.append({
                    "raw": t,
                    "clean": clean,
                    "left": l11,
                    "top": t11,
                    "width": w11,
                    "height": h11,
                    "conf": int(d11["conf"][i]) if "conf" in d11 else 50,
                })

        # Geometric reading order: dynamic line clustering (words within 25px top difference)
        words.sort(key=lambda w: w["top"])
        lines = []
        for w in words:
            assigned = False
            for line in lines:
                if abs(line["y"] - w["top"]) < 25:
                    line["words"].append(w)
                    line["y"] = (line["y"] * (len(line["words"]) - 1) + w["top"]) / len(line["words"])
                    assigned = True
                    break
            if not assigned:
                lines.append({"y": float(w["top"]), "words": [w]})
        lines.sort(key=lambda l: l["y"])
        ordered_words = []
        for line in lines:
            line["words"].sort(key=lambda w: w["left"])
            ordered_words.extend(line["words"])
        return ordered_words

    except Exception as e:
        logger.warning("OCR extraction failed: %s", e)
        return []


def _find_phrase_box(target_phrase: str, words: List[dict], min_score: float = 60.0) -> Optional[dict]:
    """
    Locates a multi-word phrase in the OCR words using token-span alignment.
    Eliminates false matches on stop-words or 1-letter substrings.
    Trims leading field label headers when separated by large horizontal gaps.
    """
    if not target_phrase or not target_phrase.strip() or not words:
        return None

    clean_target = re.sub(r"[^\w\s]", " ", target_phrase).lower().strip()
    target_tokens = clean_target.split()
    # Filter common salutations if other tokens exist
    filtered = [t for t in target_tokens if t not in ["mr", "mrs", "ms", "dr", "shri", "smt"]]
    tokens_to_match = filtered if filtered else target_tokens

    target_str = " ".join(tokens_to_match)
    k = len(tokens_to_match)
    if k == 0:
        return None

    from rapidfuzz import fuzz

    best_box = None
    best_score = 0.0
    best_text = ""

    # Sliding window around the target length (k-1 to k+4)
    min_w = max(1, k - 1)
    max_w = min(len(words), k + 4)

    for win_len in range(min_w, max_w + 1):
        for i in range(len(words) - win_len + 1):
            span = words[i:i + win_len]

            # Verify that words in span belong to roughly the same line/area
            tops = [w["top"] for w in span]
            bottoms = [w["top"] + w["height"] for w in span]
            if (max(bottoms) - min(tops)) > 150 and win_len > 1:
                continue

            span_str = " ".join(w["clean"] for w in span)
            sort_score = fuzz.token_sort_ratio(target_str, span_str)
            char_score = fuzz.ratio(target_str, span_str)
            score = (sort_score * 0.7) + (char_score * 0.3)

            # Slight penalty if window is much longer than target
            if win_len > k:
                score *= (0.95 ** (win_len - k))

            if score > best_score and score >= min_score:
                best_score = score
                val_span = list(span)
                # If first token is an isolated field label header with a large horizontal gap (>120px) to value:
                if (
                    len(val_span) > 1
                    and val_span[0]["clean"] in ["class", "subject", "seat", "name", "division"]
                    and (val_span[1]["left"] - (val_span[0]["left"] + val_span[0]["width"])) > 120
                ):
                    val_span = val_span[1:]

                # Expand horizontally across immediate continuation tokens on the same line
                last_idx = words.index(val_span[-1])
                while last_idx + 1 < len(words):
                    next_w = words[last_idx + 1]
                    if (
                        abs(next_w["top"] - val_span[-1]["top"]) < 25
                        and 0 <= (next_w["left"] - (words[last_idx]["left"] + words[last_idx]["width"])) < 120
                    ):
                        val_span.append(next_w)
                        last_idx += 1
                    else:
                        break

                x1 = min(w["left"] for w in val_span)
                y1 = min(w["top"] for w in val_span)
                x2 = max(w["left"] + w["width"] for w in val_span)
                y2 = max(w["top"] + w["height"] for w in val_span)
                best_box = [x1, y1, x2 - x1, y2 - y1]
                best_text = " ".join(w["raw"] for w in val_span)

    return {"box": best_box, "score": best_score, "text": best_text} if best_box else None


_NUMBER_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
    11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
    16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen",
    20: "twenty", 30: "thirty", 40: "forty", 50: "fifty"
}

_ORDINAL_WORDS = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
    6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
    11: "eleven", 12: "twelfth", 13: "thirteenth", 14: "fourteenth", 15: "fifteenth",
    16: "sixteenth", 17: "seventeenth", 18: "eighteenth", 19: "nineteenth",
    20: "twentieth", 21: "twenty-first", 22: "twenty-second", 23: "twenty-third",
    24: "twenty-fourth", 25: "twenty-fifth", 26: "twenty-sixth", 27: "twenty-seventh",
    28: "twenty-eighth", 29: "twenty-ninth", 30: "thirtieth", 31: "thirty-first"
}

_MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]


def _int_to_words(n: int) -> str:
    """Convert year or integer to English words, e.g. 2025 -> 'two thousand twenty five'"""
    if n in _NUMBER_WORDS:
        return _NUMBER_WORDS[n]
    if n < 100:
        tens = (n // 10) * 10
        rem = n % 10
        return f"{_NUMBER_WORDS.get(tens, '')} {_NUMBER_WORDS.get(rem, '')}".strip()
    if 100 <= n < 1000:
        h = n // 100
        rem = n % 100
        rem_str = f" {_int_to_words(rem)}" if rem else ""
        return f"{_NUMBER_WORDS.get(h, '')} hundred{rem_str}".strip()
    if 1000 <= n < 10000:
        th = n // 1000
        rem = n % 1000
        rem_str = f" {_int_to_words(rem)}" if rem else ""
        return f"{_NUMBER_WORDS.get(th, '')} thousand{rem_str}".strip()
    return str(n)


def _get_year_variants(year_int: int) -> List[str]:
    """Generate numeric and spoken forms of year, e.g. 2025 -> ['2025', 'twenty twenty five', 'two thousand twenty five']"""
    if not year_int:
        return []
    variants = [str(year_int), str(year_int)[-2:]]
    words_formal = _int_to_words(year_int)
    variants.append(words_formal)
    variants.append(words_formal.replace("thousand ", "thousand and "))

    if 2000 <= year_int < 2100:
        c = year_int // 100
        rem = year_int % 100
        if rem > 0:
            variants.append(f"{_NUMBER_WORDS.get(c, '')} {_int_to_words(rem)}".strip())
    return [v for v in variants if v]


def _get_day_variants(day_int: int) -> List[str]:
    """Generate day variants: '24', '24th', 'twenty-fourth', 'twenty fourth', plus OCR digit aliases"""
    if not day_int:
        return []
    variants = [str(day_int), f"{day_int:02d}", f"{day_int}th", f"{day_int}st", f"{day_int}nd", f"{day_int}rd"]
    if day_int in _ORDINAL_WORDS:
        ord_w = _ORDINAL_WORDS[day_int]
        variants.append(ord_w)
        variants.append(ord_w.replace("-", " "))
    # Add OCR visual digit aliases for 1-2 digits (0 <-> o/O, 5 <-> s/S, 1 <-> i/I/l)
    s = f"{day_int:02d}"
    alias = s.replace("0", "o").replace("5", "s").replace("1", "i")
    if alias != s:
        variants.append(alias)
    s1 = str(day_int)
    alias1 = s1.replace("5", "s").replace("1", "i")
    if alias1 != s1:
        variants.append(alias1)
    return variants


def _find_date_box(date_str: str, words: List[dict]) -> Optional[dict]:
    """
    Robust date localisation on certificates supporting:
      1. Numeric dates: 24-05-2024, 16-09-2013, 18/12/2021
      2. Abbreviated dates: 16-SEP-2013, APR 05 2013, APROS 2013
      3. Ceremonial prose: '24th day of the month July two thousand twenty five',
         'THIS TENTH DAY OF JUNE IN THE YEAR TWO THOUSAND AND TEN',
         'on this twelfth day of December, two thousand twenty four'.
    """
    if not date_str or not date_str.strip() or not words:
        return None

    from rapidfuzz import fuzz

    # 1. Direct exact match check
    for w in words:
        if date_str in w["raw"] or date_str in w["clean"]:
            return {"box": [w["left"], w["top"], w["width"], w["height"]], "score": 100.0, "text": w["raw"]}

    # 2. Parse date components (Day, Month, Year)
    m = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", date_str)
    day_int = int(m.group(1)) if m else None
    month_int = int(m.group(2)) if m else None
    year_int = int(m.group(3)) if m else None

    m_name = _MONTH_NAMES[month_int - 1] if month_int and 1 <= month_int <= 12 else ""
    m_short = m_name[:3] if m_name else ""
    day_vars = _get_day_variants(day_int) if day_int else []
    year_vars = _get_year_variants(year_int) if year_int else []

    best_span = None
    best_score = 0.0

    # 3. Sliding window over OCR word sequence (1 to 28 tokens)
    # Allows vertical span up to 220px to connect 2 adjacent ceremonial lines
    for win_len in range(1, min(len(words), 29)):
        for i in range(len(words) - win_len + 1):
            span = words[i:i + win_len]

            tops = [w["top"] for w in span]
            bottoms = [w["top"] + w["height"] for w in span]
            if (max(bottoms) - min(tops)) > 220 and win_len > 1:
                continue

            span_raw = " ".join(w["raw"].lower() for w in span)
            span_clean = " ".join(w["clean"] for w in span)

            score = 0.0
            has_day = False
            has_month = False
            has_year = False

            # A. Exact numeric pattern check
            if re.search(r"\d{1,2}[-./][a-z0-9]{2,4}[-./]\d{2,4}", span_raw):
                score += 80.0
                has_day = True
                has_month = True
                has_year = True

            # B. Day match (exact number, ordinal word, OCR digit alias, or fuzzy match)
            for dv in day_vars:
                if " " in dv:
                    if dv in span_raw or dv in span_clean:
                        has_day = True
                        break
                else:
                    if dv in [w["clean"] for w in span] or dv in span_clean or re.search(rf"\b{re.escape(dv)}\b", span_raw):
                        has_day = True
                        break
            if not has_day:
                for dv in day_vars:
                    if len(dv) >= 4 and fuzz.partial_ratio(dv, span_raw) >= 78:
                        has_day = True
                        break

            # C. Month match (name, 3-letter abbreviation including 'apr' in 'apros', or fuzzy match)
            if m_name and (m_name in span_raw or fuzz.partial_ratio(m_name, span_raw) >= 78):
                has_month = True
            elif m_short and (m_short in span_raw or m_short in span_clean):
                has_month = True

            # D. Year match (numeric string or spoken word phrases)
            if str(year_int) in span_raw or str(year_int) in span_clean:
                has_year = True
            else:
                for yv in year_vars:
                    if len(yv) > 3 and yv in span_raw:
                        has_year = True
                        break
                if not has_year:
                    for yv in year_vars:
                        if len(yv) >= 6 and fuzz.partial_ratio(yv, span_raw) >= 70:
                            has_year = True
                            break

            # Scoring based on components
            if has_day:
                score += 40.0
            if has_month:
                score += 40.0
            if has_year:
                score += 40.0

            # Massive bonus when all three date components are present in this window
            if has_day and has_month and has_year:
                score += 60.0

            # Context bonus (ceremonial or label anchor)
            if any(kw in span_raw for kw in ["date", "dated", "day", "month", "year"]):
                score += 15.0

            if score >= 90.0:
                # Include preceding ceremonial anchor words if adjacent on the same line
                start_idx = i
                while start_idx > 0 and abs(words[start_idx]["top"] - words[start_idx - 1]["top"]) < 35:
                    prev_raw = words[start_idx - 1]["raw"].lower().strip(":.,")
                    if prev_raw in ["on", "this", "the", "dated", "date"]:
                        start_idx -= 1
                    else:
                        break

                # Include succeeding year continuation words if adjacent on the same line
                end_idx = i + win_len
                while end_idx < len(words) and abs(words[end_idx]["top"] - words[end_idx - 1]["top"]) < 35:
                    next_raw = words[end_idx]["clean"].lower()
                    if next_raw in [
                        "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                        "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
                        "eighteen", "nineteen", "twenty", "thirty", "and"
                    ]:
                        end_idx += 1
                    else:
                        break

                full_span = words[start_idx:end_idx]
                quality = score - (win_len * 0.2)
                if quality > best_score:
                    best_score = quality
                    best_span = full_span

    if best_span:
        x1 = min(w["left"] for w in best_span)
        y1 = min(w["top"] for w in best_span)
        x2 = max(w["left"] + w["width"] for w in best_span)
        y2 = max(w["top"] + w["height"] for w in best_span)
        return {
            "box": [x1, y1, x2 - x1, y2 - y1],
            "score": best_score,
            "text": " ".join(w["raw"] for w in best_span)
        }

    return None


def _find_field_boxes(
    fields: Dict[str, str],
    words: List[dict],
    img_w: int,
    img_h: int
) -> Dict[str, Optional[List[int]]]:
    """
    High-precision field localisation mapping extracted fields to bounding boxes.
    """
    boxes: Dict[str, Optional[List[int]]] = {f: None for f in FIELDS}
    if not words:
        return boxes

    for field_name, field_val in fields.items():
        if not field_val or len(field_val.strip()) < 2:
            continue

        if field_name == "issue_date":
            res = _find_date_box(field_val, words)
        else:
            res = _find_phrase_box(field_val, words)

        if res and res.get("box"):
            x, y, w, h = res["box"]
            # Add subtle padding and clamp within image boundaries
            pad = 5
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(img_w, x + w + pad)
            y2 = min(img_h, y + h + pad)
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
        from PIL import ImageOps
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img).convert("RGB")
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
            ocr_words = _get_ocr_words(img)
            field_boxes = _find_field_boxes(fields, ocr_words, img.width, img.height)
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
