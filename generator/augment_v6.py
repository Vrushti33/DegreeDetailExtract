"""Albumentations augmentation pipeline for v6 synthetic certificate images.

v6 CHANGE: Blur (GaussianBlur) has been REMOVED from the pipeline.
Rationale: Donut was pre-trained on clean document images. Blurry training
images degrade OCR token generation and produce gibberish outputs on real
(slightly blurry) certificates. Without blur augmentation the model learns
cleaner text patterns that transfer better.

Remaining augmentations simulate legitimate real-world variations:
  - Slight rotation  (camera tilt)
  - Brightness / contrast jitter  (lighting)
  - JPEG compression artifacts  (scanner/camera output quality)
  - Mild Gaussian noise  (sensor noise — kept at very low intensity)

Fails gracefully if albumentations is not installed.
"""

from typing import Optional

import numpy as np
from PIL import Image

try:
    import albumentations as A
    _ALBUMENTATIONS_AVAILABLE = True
except ImportError:
    _ALBUMENTATIONS_AVAILABLE = False


def _build_pipeline_v6() -> Optional["A.Compose"]:
    """Construct the v6 (blur-free) augmentation pipeline."""
    if not _ALBUMENTATIONS_AVAILABLE:
        return None

    transforms = [
        # Slight rotation (±2°) — reduced from ±3° to keep text crisp
        A.Rotate(limit=2, border_mode=0, value=(255, 255, 255), p=0.60),
        # Gentle perspective warp — simulates off-axis photo angle
        A.Perspective(scale=(0.01, 0.03), p=0.25),
        # Brightness / contrast — lighting variation
        A.RandomBrightnessContrast(
            brightness_limit=0.12, contrast_limit=0.12, p=0.60
        ),
        # JPEG compression artifacts — simulates camera or scanner output
        # quality_lower raised to 72 (was 62) to keep text readable
        A.ImageCompression(quality_lower=72, quality_upper=97, p=0.40),
    ]

    # Very mild Gaussian noise (sensor noise only — NOT blur)
    for noise_kwargs in [
        {"var_limit": (2.0, 10.0), "p": 0.30},   # v1.x / early v2
        {"p": 0.30},                               # minimal fallback
    ]:
        try:
            transforms.insert(2, A.GaussNoise(**noise_kwargs))
            break
        except (TypeError, AttributeError):
            continue

    return A.Compose(transforms)


# Build pipeline once at import time
_PIPELINE_V6: Optional["A.Compose"] = None


def augment_image_v6(pil_image: Image.Image) -> Image.Image:
    """Apply the v6 (blur-free) augmentation pipeline to *pil_image*.

    Parameters
    ----------
    pil_image:
        Input PIL image (any mode; converted to RGB internally).

    Returns
    -------
    Augmented PIL image in RGB mode.  If albumentations is unavailable or
    an error occurs the original image (converted to RGB) is returned
    unchanged.
    """
    global _PIPELINE_V6

    if not _ALBUMENTATIONS_AVAILABLE:
        return pil_image.convert("RGB")

    if _PIPELINE_V6 is None:
        _PIPELINE_V6 = _build_pipeline_v6()

    if _PIPELINE_V6 is None:
        return pil_image.convert("RGB")

    try:
        arr = np.array(pil_image.convert("RGB"))
        result = _PIPELINE_V6(image=arr)["image"]
        return Image.fromarray(result)
    except Exception:
        return pil_image.convert("RGB")
