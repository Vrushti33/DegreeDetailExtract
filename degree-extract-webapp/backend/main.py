"""
DegreeDetailExtract — FastAPI backend.

Loads the fine-tuned Donut model once at startup and exposes a single
/extract endpoint that accepts a degree certificate image and returns the
extracted fields as JSON.
"""

from __future__ import annotations  # allows `X | None` type hints on Python 3.9 too

import io
import os
import re
import logging

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from transformers import DonutProcessor, VisionEncoderDecoderModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("degree-extract")

# ── Configuration ──────────────────────────────────────────────────────────
# MODEL_SOURCE can be either:
#   - a HuggingFace Hub repo id, e.g. "your-username/degree-extract-donut"
#     (recommended for deployment — see backend/README.md for how to push
#     your Colab checkpoint there)
#   - a local directory path containing the saved checkpoint
MODEL_SOURCE = os.environ.get("MODEL_SOURCE", "your-username/degree-extract-donut")
HF_TOKEN = os.environ.get("HF_TOKEN")  # only needed if MODEL_SOURCE is a private HF repo

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

app = FastAPI(title="DegreeDetailExtract API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ── Model loading (once, at startup) ───────────────────────────────────────
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


# ── Helpers ─────────────────────────────────────────────────────────────────
def _parse_fields(pred_str: str) -> dict:
    result = {}
    for f in FIELDS:
        m = re.search(rf"<s_{f}>(.*?)</s_{f}>", pred_str, re.DOTALL)
        result[f] = m.group(1).strip() if m else ""
    return result


def _run_inference(img: Image.Image) -> dict:
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
            max_new_tokens=128,
        )
    pred_str = processor.tokenizer.decode(outputs[0], skip_special_tokens=False)
    return _parse_fields(pred_str)


# ── Routes ──────────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": model is not None, "device": device}


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
        fields = _run_inference(img)
    except Exception:
        logger.exception("Inference failed")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while reading this certificate. Please try again.",
        )

    missing = [f for f in FIELDS if not fields.get(f)]
    return {"fields": fields, "missing_fields": missing}
