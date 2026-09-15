"""v3 Certificate Renderer — 36-template anti-overfitting pipeline.

New templates (t29–t36) are weighted 3× more than original templates so the
model is exposed primarily to the new, more realistic certificate styles.

Usage
-----
    from generator.renderer_v3 import init_bg_pool, render_certificate_v3

    init_bg_pool("/content/DegreeDetailExtract/real_certs")
    img = render_certificate_v3(fields, augment=True)
"""

import random
from pathlib import Path
from typing import List, Optional

from PIL import Image

from .templates    import TEMPLATES          # 22 original
from .templates_v2 import TEMPLATES_V2      # 6 v2 templates
from .templates_v3 import TEMPLATES_V3, BG_POOL as _V3_BG_POOL
import generator.templates_v2 as _tv2_module
import generator.templates_v3 as _tv3_module
from .augment import augment_image


# ── Combined pool: 22 original + 6 v2 + 8 v3 = 36 ───────────────────────────
ALL_TEMPLATES = TEMPLATES + TEMPLATES_V2 + TEMPLATES_V3

_WEIGHTS = (
    [1.0] * len(TEMPLATES) +    # original: 1×
    [2.0] * len(TEMPLATES_V2) + # v2:       2×
    [3.0] * len(TEMPLATES_V3)   # v3:       3× (most realistic)
)


def init_bg_pool(real_certs_dir: str) -> int:
    """Load real-certificate backgrounds into ALL texture-using template pools."""
    from .realistic_bg import get_background_pool

    pool = get_background_pool(real_certs_dir)

    _tv2_module.BG_POOL.clear()
    _tv2_module.BG_POOL.extend(pool)

    _tv3_module.BG_POOL.clear()
    _tv3_module.BG_POOL.extend(pool)

    return len(pool)


def render_certificate_v3(
    fields: dict,
    augment: bool = True,
    template_idx: Optional[int] = None,
    only_v3: bool = False,
    only_new: bool = False,
) -> Image.Image:
    """Render a single certificate using the v3 pipeline.

    Parameters
    ----------
    fields       : dict of 7 certificate fields (pass_class may be empty)
    augment      : apply heavy augmentation pipeline
    template_idx : fixed template index; None = weighted random
    only_v3      : only pick from 8 new v3 templates
    only_new     : only pick from 14 new templates (v2 + v3)
    """
    if only_v3:
        pool    = TEMPLATES_V3
        weights = [3.0] * len(TEMPLATES_V3)
    elif only_new:
        pool    = TEMPLATES_V2 + TEMPLATES_V3
        weights = [2.0] * len(TEMPLATES_V2) + [3.0] * len(TEMPLATES_V3)
    else:
        pool    = ALL_TEMPLATES
        weights = _WEIGHTS

    if template_idx is not None:
        fn = pool[template_idx % len(pool)]
    else:
        fn = random.choices(pool, weights=weights, k=1)[0]

    img = fn(fields)

    if augment:
        img = _augment_heavy(img)
    else:
        img = img.convert("RGB")

    return img


# ── Augmentation pipeline (v3 — slightly heavier) ────────────────────────────
def _augment_heavy(pil_image: Image.Image) -> Image.Image:
    """Simulate phone-camera or scanner artefacts on the certificate."""
    try:
        import albumentations as A
        import numpy as np

        pipeline = A.Compose([
            A.Rotate(limit=6, border_mode=0, value=(240, 235, 220), p=0.80),
            A.Perspective(scale=(0.02, 0.07), p=0.55),
            A.GaussianBlur(blur_limit=(3, 9), p=0.45),
            A.RandomBrightnessContrast(
                brightness_limit=0.30, contrast_limit=0.25, p=0.80
            ),
            A.ImageCompression(quality_lower=50, quality_upper=95, p=0.65),
            A.HueSaturationValue(
                hue_shift_limit=8, sat_shift_limit=20, val_shift_limit=20, p=0.45
            ),
            A.RandomShadow(num_shadows_lower=1, num_shadows_upper=2,
                           shadow_dimension=5, p=0.25),
            A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.3), p=0.30),
        ])

        arr    = np.array(pil_image.convert("RGB"))
        result = pipeline(image=arr)["image"]
        return Image.fromarray(result)
    except Exception:
        return augment_image(pil_image)


__all__ = ["init_bg_pool", "render_certificate_v3", "ALL_TEMPLATES"]
