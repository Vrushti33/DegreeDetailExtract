"""Real certificate background texture extractor.

Loads real degree certificate images from *real_certs_dir*, inpaints
(removes) the variable text regions to preserve the blank paper texture,
and returns cached background tiles for blending into synthetic templates.

Also extracts dominant ink colours from each scan to allow templates to
match the ink tone of real certificates.

Usage
-----
    from generator.realistic_bg import get_background_pool, sample_background, sample_ink_color

    pool = get_background_pool("/content/DegreeDetailExtract/real_certs")
    bg   = sample_background(pool, target_size=(1000, 1400))
    ink  = sample_ink_color(pool)
"""

import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image


# ── Optional OpenCV import ─────────────────────────────────────────────────────
try:
    import cv2 as _cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────────────────
#  Data structures
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class CertTexture:
    """Stores inpainted background + ink palette for one real certificate."""
    background: Image.Image          # inpainted blank background (RGB)
    ink_colors: List[Tuple[int, int, int]]  # top-5 dark ink colors (RGB)
    source_path: str                 # original file path (for debugging)


# ──────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _load_image_rgb(path: Path) -> Optional[Image.Image]:
    """Load any image (JPEG / PNG / WebP) and return an RGB PIL Image."""
    try:
        img = Image.open(str(path)).convert("RGB")
        return img
    except Exception:
        return None


def _inpaint_text(img_pil: Image.Image) -> Image.Image:
    """Remove text from a certificate scan to expose the paper background.

    Strategy:
    1. Convert to grayscale, adaptive-threshold to isolate dark ink pixels.
    2. Dilate the mask slightly so thin strokes are fully covered.
    3. Use cv2.inpaint (Telea method) to fill the masked regions.

    Falls back gracefully to a Gaussian-blurred version if OpenCV is absent.
    """
    arr = np.array(img_pil.convert("RGB"))

    if not _CV2_AVAILABLE:
        # Fallback: aggressive Gaussian blur hides text while keeping texture
        from PIL import ImageFilter
        blurred = img_pil.filter(ImageFilter.GaussianBlur(radius=8))
        return blurred.convert("RGB")

    gray = _cv2.cvtColor(arr, _cv2.COLOR_RGB2GRAY)

    # Adaptive threshold — isolates dark ink on any background color
    thresh = _cv2.adaptiveThreshold(
        gray, 255,
        _cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        _cv2.THRESH_BINARY_INV,
        blockSize=25, C=12,
    )

    # Remove tiny specks (noise) but keep strokes
    kernel = np.ones((3, 3), np.uint8)
    mask   = _cv2.dilate(thresh, kernel, iterations=2)

    # Inpaint: Telea algorithm fills each masked pixel from its neighbourhood
    inpainted_bgr = _cv2.inpaint(
        _cv2.cvtColor(arr, _cv2.COLOR_RGB2BGR),
        mask, inpaintRadius=4,
        flags=_cv2.INPAINT_TELEA,
    )
    return Image.fromarray(_cv2.cvtColor(inpainted_bgr, _cv2.COLOR_BGR2RGB))


def _extract_ink_colors(img_pil: Image.Image, n: int = 5) -> List[Tuple[int, int, int]]:
    """Return up to *n* representative dark ink colors from the image.

    Dark pixels (luminance < 100) are k-means clustered to find the
    dominant ink color family. Falls back to common ink defaults if
    clustering fails (no scipy / OpenCV).
    """
    arr  = np.array(img_pil.convert("RGB"), dtype=np.float32)
    dark = arr[(arr[..., 0] < 100) & (arr[..., 1] < 100) & (arr[..., 2] < 100)]

    if len(dark) < 50:
        # Mostly light document — return sensible dark defaults
        return [(20, 20, 20), (10, 40, 80), (60, 0, 20), (0, 60, 40), (50, 30, 0)]

    # Simple quantile-based sampling (no sklearn needed)
    sample_idx = np.random.choice(len(dark), size=min(500, len(dark)), replace=False)
    sample = dark[sample_idx].astype(int)

    # Return up to n unique colors from the sample (deduplicated by rounding)
    rounded = set()
    result: List[Tuple[int, int, int]] = []
    for px in sample:
        key = (int(px[0] // 30) * 30, int(px[1] // 30) * 30, int(px[2] // 30) * 30)
        if key not in rounded:
            rounded.add(key)
            result.append((int(px[0]), int(px[1]), int(px[2])))
        if len(result) >= n:
            break

    return result if result else [(20, 20, 20)]


# ──────────────────────────────────────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────────────────────────────────────

_POOL_CACHE: Optional[List[CertTexture]] = None
_POOL_DIR: Optional[str] = None


def get_background_pool(real_certs_dir: str) -> List[CertTexture]:
    """Build (and cache) the pool of inpainted certificate backgrounds.

    Parameters
    ----------
    real_certs_dir:
        Path to a directory containing real certificate scans
        (JPEG / PNG / WebP).

    Returns
    -------
    List of CertTexture objects (empty list if directory has no images).
    """
    global _POOL_CACHE, _POOL_DIR

    real_certs_dir = str(real_certs_dir)
    if _POOL_CACHE is not None and _POOL_DIR == real_certs_dir:
        return _POOL_CACHE

    pool: List[CertTexture] = []
    certs_path = Path(real_certs_dir)

    if not certs_path.is_dir():
        _POOL_CACHE = pool
        _POOL_DIR   = real_certs_dir
        return pool

    supported = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
    image_paths = [
        p for p in sorted(certs_path.iterdir())
        if p.suffix.lower() in supported
    ]

    print(f"[realistic_bg] Processing {len(image_paths)} real certificate(s)...")

    for p in image_paths:
        img = _load_image_rgb(p)
        if img is None:
            continue
        try:
            bg       = _inpaint_text(img)
            ink_cols = _extract_ink_colors(img)
            pool.append(CertTexture(
                background=bg,
                ink_colors=ink_cols,
                source_path=str(p),
            ))
        except Exception as e:
            print(f"[realistic_bg] Skipping {p.name}: {e}")

    print(f"[realistic_bg] Background pool ready: {len(pool)} textures.")
    _POOL_CACHE = pool
    _POOL_DIR   = real_certs_dir
    return pool


def sample_background(
    pool: List[CertTexture],
    target_size: Tuple[int, int] = (1000, 1400),
    blend_alpha: float = 0.35,
    base_color: Optional[Tuple[int, int, int]] = None,
) -> Image.Image:
    """Return a background image for use in a synthetic template.

    If *pool* is non-empty, a random real-certificate background is
    resized, optionally colour-tinted, and returned.

    If *pool* is empty, a plain-colour background using *base_color* is
    returned (matching the behaviour before this module was added).

    Parameters
    ----------
    pool:
        List returned by ``get_background_pool()``.
    target_size:
        (width, height) in pixels.
    blend_alpha:
        How strongly the real background texture shows through (0 = none,
        1 = full texture, no synthetic tint).
    base_color:
        RGB tuple for the synthetic base colour.  Defaults to a warm cream.
    """
    W, H = target_size
    if base_color is None:
        base_color = (253, 251, 240)

    if not pool:
        return Image.new("RGB", (W, H), base_color)

    texture  = random.choice(pool)
    bg_resized = texture.background.resize((W, H), Image.LANCZOS)

    # Blend: mix synthetic base color with real background
    base_img  = Image.new("RGB", (W, H), base_color)
    blended   = Image.blend(base_img, bg_resized, alpha=blend_alpha)
    return blended


def sample_ink_color(pool: List[CertTexture]) -> Tuple[int, int, int]:
    """Return a random ink colour from the pool (or a sensible default)."""
    if not pool:
        return (20, 20, 20)
    texture = random.choice(pool)
    return random.choice(texture.ink_colors) if texture.ink_colors else (20, 20, 20)


__all__ = [
    "CertTexture",
    "get_background_pool",
    "sample_background",
    "sample_ink_color",
]
