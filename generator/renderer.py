"""Pillow-only certificate renderer.

Picks a template (randomly or by index) and optionally applies
the Albumentations augmentation pipeline.
"""

import random
from typing import Optional

from PIL import Image

from .templates import TEMPLATES
from .augment import augment_image


def render_certificate(
    fields: dict,
    augment: bool = True,
    template_idx: Optional[int] = None,
) -> Image.Image:
    """Render a single synthetic certificate image.

    Parameters
    ----------
    fields:
        Dict with keys: student_name, university_name, course_name,
        specialization, pass_class, authority_name, issue_date.
    augment:
        Whether to apply the augmentation pipeline after rendering.
        Set to False for clean template previews.
    template_idx:
        If given, select ``TEMPLATES[template_idx % len(TEMPLATES)]``.
        If None (default), a template is chosen at random.

    Returns
    -------
    PIL Image in RGB mode (1000 × 1400 px before augmentation).
    """
    if template_idx is None:
        template_fn = random.choice(TEMPLATES)
    else:
        template_fn = TEMPLATES[template_idx % len(TEMPLATES)]

    img = template_fn(fields)

    if augment:
        img = augment_image(img)
    else:
        img = img.convert("RGB")

    return img


__all__ = ["render_certificate"]
