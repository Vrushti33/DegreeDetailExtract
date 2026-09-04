"""Albumentations augmentation pipeline for synthetic certificate images.

Simulates real-world photo/scan conditions: slight rotation, perspective
warp, noise, blur, brightness/contrast jitter, and JPEG compression
artifacts.  Fails gracefully if albumentations is not installed.
"""

from typing import Optional

import numpy as np
from PIL import Image

try:
    import albumentations as A
    _ALBUMENTATIONS_AVAILABLE = True
except ImportError:
    _ALBUMENTATIONS_AVAILABLE = False


def _build_pipeline() -> Optional["A.Compose"]:
    """Construct the augmentation pipeline.

    Handles API differences across albumentations versions (1.x vs 2.x).
    """
    if not _ALBUMENTATIONS_AVAILABLE:
        return None

    transforms = [
        # Slight rotation (±3°) — simulates handheld photo tilt
        A.Rotate(limit=3, border_mode=0, value=(255, 255, 255), p=0.70),
        # Gentle perspective warp — simulates off-axis photo angle
        A.Perspective(scale=(0.01, 0.04), p=0.35),
        # Soft blur — simulates camera shake / out-of-focus scan
        A.GaussianBlur(blur_limit=(3, 5), p=0.30),
        # Brightness / contrast — lighting variation
        A.RandomBrightnessContrast(
            brightness_limit=0.15, contrast_limit=0.15, p=0.60
        ),
        # JPEG compression artifacts — simulates camera or scanner output
        A.ImageCompression(quality_lower=62, quality_upper=97, p=0.50),
    ]

    # GaussNoise API varies across albumentations versions
    for noise_kwargs in [
        {"var_limit": (5.0, 25.0), "p": 0.45},   # v1.x / early v2
        {"p": 0.45},                               # minimal fallback
    ]:
        try:
            transforms.insert(2, A.GaussNoise(**noise_kwargs))
            break
        except (TypeError, AttributeError):
            continue

    return A.Compose(transforms)


# Build pipeline once at import time
_PIPELINE: Optional["A.Compose"] = None


def augment_image(pil_image: Image.Image) -> Image.Image:
    """Apply the augmentation pipeline to *pil_image*.

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
    global _PIPELINE

    if not _ALBUMENTATIONS_AVAILABLE:
        return pil_image.convert("RGB")

    if _PIPELINE is None:
        _PIPELINE = _build_pipeline()

    if _PIPELINE is None:
        return pil_image.convert("RGB")

    try:
        arr = np.array(pil_image.convert("RGB"))
        result = _PIPELINE(image=arr)["image"]
        return Image.fromarray(result)
    except Exception:
        return pil_image.convert("RGB")
