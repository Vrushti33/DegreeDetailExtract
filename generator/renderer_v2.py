"""v2 Certificate Renderer — uses real background textures + ceremonial prose.

Extends the original renderer with:
- Real paper backgrounds (from ``realistic_bg``)
- 6 new prose-heavy templates (t23–t28)
- Heavier augmentation for phone-camera simulation

Usage
-----
    from generator.renderer_v2 import init_bg_pool, render_certificate_v2

    init_bg_pool("/content/DegreeDetailExtract/real_certs")
    img = render_certificate_v2(fields, augment=True)
"""

import random
from pathlib import Path
from typing import List, Optional

from PIL import Image

from .templates import TEMPLATES
from .templates_v2 import TEMPLATES_V2, BG_POOL as _V2_BG_POOL
import generator.templates_v2 as _tv2_module
from .augment import augment_image


# ── Combined template pool: 22 original + 6 new = 28 ─────────────────────────
ALL_TEMPLATES = TEMPLATES + TEMPLATES_V2

# Weight new templates 2x so they appear more often (anti-overfitting boost)
_WEIGHTS = [1.0] * len(TEMPLATES) + [2.0] * len(TEMPLATES_V2)


def init_bg_pool(real_certs_dir: str) -> int:
    """Load and cache real-certificate backgrounds into the v2 template pool.

    Parameters
    ----------
    real_certs_dir:
        Path to a directory with real certificate images.
        Pass an empty string or a non-existent path to skip texture loading
        (templates fall back to flat colours).

    Returns
    -------
    Number of backgrounds loaded (0 if directory is missing or empty).
    """
    from .realistic_bg import get_background_pool

    pool = get_background_pool(real_certs_dir)

    # Inject pool into templates_v2 module so t23–t28 can use it
    _tv2_module.BG_POOL.clear()
    _tv2_module.BG_POOL.extend(pool)

    return len(pool)


def render_certificate_v2(
    fields: dict,
    augment: bool = True,
    template_idx: Optional[int] = None,
    use_only_new: bool = False,
) -> Image.Image:
    """Render a single certificate using the v2 pipeline.

    Parameters
    ----------
    fields:
        Dict with 7 certificate fields.
    augment:
        Whether to apply augmentation pipeline.
    template_idx:
        Fixed template index (cycles through ALL_TEMPLATES). None = random.
    use_only_new:
        If True, only pick from the 6 new prose+texture templates.

    Returns
    -------
    RGB PIL Image (1000 × 1400 px before augmentation).
    """
    pool = TEMPLATES_V2 if use_only_new else ALL_TEMPLATES
    weights = [2.0] * len(TEMPLATES_V2) if use_only_new else _WEIGHTS

    if template_idx is not None:
        template_fn = pool[template_idx % len(pool)]
    else:
        template_fn = random.choices(pool, weights=weights, k=1)[0]

    img = template_fn(fields)

    if augment:
        img = _augment_heavy(img)
    else:
        img = img.convert("RGB")

    return img


# ── Heavier augmentation pipeline ─────────────────────────────────────────────
def _augment_heavy(pil_image: Image.Image) -> Image.Image:
    """Apply heavier augmentation simulating phone-camera certificate photos."""
    try:
        import albumentations as A
        import numpy as np

        pipeline = A.Compose([
            A.Rotate(limit=5, border_mode=0, value=(255, 255, 255), p=0.75),
            A.Perspective(scale=(0.02, 0.06), p=0.50),
            A.GaussianBlur(blur_limit=(3, 7), p=0.40),
            A.RandomBrightnessContrast(
                brightness_limit=0.25, contrast_limit=0.20, p=0.75
            ),
            A.ImageCompression(quality_lower=55, quality_upper=95, p=0.60),
            A.HueSaturationValue(
                hue_shift_limit=5, sat_shift_limit=15, val_shift_limit=15, p=0.40
            ),
        ])

        arr    = np.array(pil_image.convert("RGB"))
        result = pipeline(image=arr)["image"]
        return Image.fromarray(result)
    except Exception:
        return augment_image(pil_image)   # fallback to original augment


__all__ = ["init_bg_pool", "render_certificate_v2", "ALL_TEMPLATES"]
