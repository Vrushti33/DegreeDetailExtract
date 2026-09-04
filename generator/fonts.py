"""Font loading utilities for Pillow-based certificate templates.

Searches common font directories on both Windows and Linux/Colab.
Falls back gracefully to PIL's built-in default font if no system
TrueType fonts are found.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from PIL import ImageFont

# ── Search directories (Windows + Linux/Colab + macOS) ────────────────────────
_FONT_DIRS: List[str] = [
    # Windows
    "C:/Windows/Fonts",
    # Linux / Google Colab (standard locations)
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/liberation2",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/freefont",
    "/usr/share/fonts/truetype/msttcorefonts",
    "/usr/share/fonts/truetype",
    "/usr/share/fonts",
    # User-local
    os.path.expanduser("~/.fonts"),
    os.path.expanduser("~/Library/Fonts"),  # macOS
    "/System/Library/Fonts",                 # macOS
    "/Library/Fonts",                        # macOS
]

# ── Font filename candidates per style (tried left-to-right; first hit wins) ──
_FONT_FILES: Dict[str, List[str]] = {
    "serif_regular": [
        "times.ttf", "Times New Roman.ttf", "TimesNewRoman.ttf",
        "LiberationSerif-Regular.ttf", "FreeSerif.ttf", "DejaVuSerif.ttf",
    ],
    "serif_bold": [
        "timesbd.ttf", "Times New Roman Bold.ttf", "TimesNewRomanBold.ttf",
        "LiberationSerif-Bold.ttf", "FreeSerifBold.ttf", "DejaVuSerif-Bold.ttf",
    ],
    "serif_italic": [
        "timesi.ttf", "Times New Roman Italic.ttf",
        "LiberationSerif-Italic.ttf", "FreeSerifItalic.ttf",
        "DejaVuSerif-Oblique.ttf",
    ],
    "sans_regular": [
        "arial.ttf", "Arial.ttf",
        "LiberationSans-Regular.ttf", "FreeSans.ttf", "DejaVuSans.ttf",
    ],
    "sans_bold": [
        "arialbd.ttf", "Arial Bold.ttf",
        "LiberationSans-Bold.ttf", "FreeSansBold.ttf", "DejaVuSans-Bold.ttf",
    ],
    "georgia_regular": [
        "georgia.ttf", "Georgia.ttf",
        "LiberationSerif-Regular.ttf", "FreeSerif.ttf", "DejaVuSerif.ttf",
    ],
    "georgia_bold": [
        "georgiab.ttf", "Georgia Bold.ttf",
        "LiberationSerif-Bold.ttf", "FreeSerifBold.ttf", "DejaVuSerif-Bold.ttf",
    ],
    "calibri": [
        "calibri.ttf", "Calibri.ttf",
        "LiberationSans-Regular.ttf", "FreeSans.ttf", "DejaVuSans.ttf",
    ],
}

# Module-level cache: (style, size) -> ImageFont
_cache: Dict[tuple, ImageFont.ImageFont] = {}


def _find_font_path(style: str) -> Optional[str]:
    """Return the absolute path of the first font file found for *style*."""
    for fname in _FONT_FILES.get(style, []):
        for d in _FONT_DIRS:
            p = Path(d) / fname
            if p.exists():
                return str(p)
    return None


def _load(style: str, size: int) -> ImageFont.ImageFont:
    """Load (and cache) a font by style + size."""
    key = (style, size)
    if key in _cache:
        return _cache[key]

    path = _find_font_path(style)
    if path:
        try:
            font = ImageFont.truetype(path, size)
            _cache[key] = font
            return font
        except Exception:
            pass

    # Graceful fallback: Pillow's built-in default font
    try:
        font = ImageFont.load_default(size=size)   # Pillow >= 10.1
    except TypeError:
        font = ImageFont.load_default()
    _cache[key] = font
    return font


def get_fonts(scale: float = 1.0) -> Dict[str, ImageFont.ImageFont]:
    """Return a dict of named font variants scaled by *scale*.

    Keys
    ----
    title, subtitle, heading, body, body_italic,
    label, value, small, geo_title, geo_body, calibri.
    """
    base = int(26 * scale)
    return {
        "title":        _load("serif_bold",     int(base * 1.70)),
        "subtitle":     _load("serif_bold",     int(base * 1.15)),
        "heading":      _load("serif_bold",     int(base * 0.95)),
        "body":         _load("serif_regular",  int(base * 0.88)),
        "body_italic":  _load("serif_italic",   int(base * 0.88)),
        "label":        _load("sans_bold",      int(base * 0.72)),
        "value":        _load("sans_regular",   int(base * 0.80)),
        "small":        _load("serif_regular",  int(base * 0.65)),
        "geo_title":    _load("georgia_bold",   int(base * 1.55)),
        "geo_body":     _load("georgia_regular",int(base * 0.88)),
        "calibri":      _load("calibri",        int(base * 0.85)),
    }
