"""Font loading utilities for Pillow-based certificate templates.

Searches common font directories on both Windows and Linux/Colab.
Falls back gracefully to PIL's built-in default font if no system
TrueType fonts are found.

Calligraphy / formal Google Fonts
----------------------------------
Real degree certificates commonly use calligraphy or engraved fonts for the
student name and institutional title.  This module supports five such fonts:

    Great Vibes        — flowing script (student name)
    Cinzel             — engraved Roman capitals (university name / title)
    IM Fell English    — antique book type (body prose, evokes printed diplomas)
    Playfair Display   — high-contrast display serif (headings)
    UnifrakturMaguntia — Old-English blackletter (dramatic title banner)

On Google Colab these are downloaded automatically by calling
``download_certificate_fonts()``.  On Windows the existing Times/Georgia
fallbacks are used so nothing breaks locally.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from PIL import ImageFont

# ── Search directories (Windows + Linux/Colab + macOS) ────────────────────────
_FONT_DIRS: List[str] = [
    # Windows
    "C:/Windows/Fonts",
    # Certificate fonts downloaded by download_certificate_fonts()
    "/content/cert_fonts",
    os.path.expanduser("~/.cert_fonts"),
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

# ── Google Fonts download manifest ────────────────────────────────────────────
# (filename, Google Fonts raw URL)
# These are OFL-licensed fonts freely usable in any project.
_GFONT_URLS: List[tuple] = [
    (
        "GreatVibes-Regular.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/greatvibes/GreatVibes-Regular.ttf",
    ),
    # ── 4 new cursive / script fonts (v4) — real certs use varied handwriting ──
    (
        "Parisienne-Regular.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/parisienne/Parisienne-Regular.ttf",
    ),
    (
        "Allura-Regular.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/allura/Allura-Regular.ttf",
    ),
    (
        "PinyonScript-Regular.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/pinyonscript/PinyonScript-Regular.ttf",
    ),
    (
        "AlexBrush-Regular.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/alexbrush/AlexBrush-Regular.ttf",
    ),
    # ── Formal / engraved ─────────────────────────────────────────────────────
    (
        "Cinzel[wght].ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/cinzel/Cinzel%5Bwght%5D.ttf",
    ),
    (
        "IMFeENrm28P.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/imfellenglish/IMFeENrm28P.ttf",
    ),
    (
        "IMFeENit28P.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/imfellenglish/IMFeENit28P.ttf",
    ),
    (
        "PlayfairDisplay[wght].ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
    ),
    (
        "PlayfairDisplay-Italic[wght].ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay-Italic%5Bwght%5D.ttf",
    ),
    (
        "UnifrakturMaguntia-Book.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/unifrakturmaguntia/UnifrakturMaguntia-Book.ttf",
    ),
]


def download_certificate_fonts(dest_dir: str = "/content/cert_fonts") -> str:
    """Download calligraphy/formal Google Fonts to *dest_dir*.

    Call this once at the top of your Colab notebook **before** any
    certificate generation.  On Windows/local the files won't be present
    but the graceful fallback chain in ``_FONT_FILES`` will kick in.

    Returns the destination directory path.
    """
    import urllib.request
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    # Also add dest to the search path at runtime
    if dest_dir not in _FONT_DIRS:
        _FONT_DIRS.insert(0, dest_dir)

    downloaded, skipped = 0, 0
    for fname, url in _GFONT_URLS:
        fpath = dest / fname
        if fpath.exists():
            skipped += 1
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                fpath.write_bytes(resp.read())
            downloaded += 1
        except Exception as e:
            print(f"[fonts] Could not download {fname}: {e}")

    # Invalidate font cache so freshly downloaded fonts are picked up
    global _cache
    _cache.clear()

    print(f"[fonts] Certificate fonts ready: {downloaded} downloaded, {skipped} already cached -> {dest_dir}")
    return dest_dir

# ── Font filename candidates per style (tried left-to-right; first hit wins) ──
_FONT_FILES: Dict[str, List[str]] = {
    # ── Calligraphy / formal (downloaded by download_certificate_fonts) ────────
    "script": [
        # 5 script fonts — randomly chosen per cert (see get_fonts)
        "GreatVibes-Regular.ttf",
        "Parisienne-Regular.ttf",
        "Allura-Regular.ttf",
        "PinyonScript-Regular.ttf",
        "AlexBrush-Regular.ttf",
        # Fallbacks if fonts not yet downloaded
        "PinyonScript.ttf", "Sacramento.ttf",
        "georgia.ttf", "Georgia.ttf",
        "timesi.ttf", "LiberationSerif-Italic.ttf",
    ],
    "script_parisienne": [
        "Parisienne-Regular.ttf",
        "GreatVibes-Regular.ttf", "Allura-Regular.ttf",
        "georgia.ttf", "timesi.ttf",
    ],
    "script_allura": [
        "Allura-Regular.ttf",
        "GreatVibes-Regular.ttf", "PinyonScript-Regular.ttf",
        "georgia.ttf", "timesi.ttf",
    ],
    "script_pinyon": [
        "PinyonScript-Regular.ttf",
        "AlexBrush-Regular.ttf", "GreatVibes-Regular.ttf",
        "georgia.ttf", "timesi.ttf",
    ],
    "script_alex": [
        "AlexBrush-Regular.ttf",
        "PinyonScript-Regular.ttf", "Allura-Regular.ttf",
        "georgia.ttf", "timesi.ttf",
    ],
    "cinzel_bold": [
        # Cinzel: engraved Roman capitals — university name
        "Cinzel[wght].ttf", "Cinzel-Bold.ttf",
        # Fallbacks
        "georgiab.ttf", "Georgia Bold.ttf",
        "timesbd.ttf", "LiberationSerif-Bold.ttf",
    ],
    "cinzel_regular": [
        "Cinzel[wght].ttf", "Cinzel-Regular.ttf",
        "georgia.ttf", "times.ttf", "LiberationSerif-Regular.ttf",
    ],
    "antique_regular": [
        # IM Fell English: antique book type — body prose (diploma-style)
        "IMFeENrm28P.ttf", "IMFellEnglish-Regular.ttf",
        # Fallbacks
        "georgia.ttf", "Georgia.ttf",
        "times.ttf", "LiberationSerif-Regular.ttf",
    ],
    "antique_italic": [
        "IMFeENit28P.ttf", "IMFellEnglish-Italic.ttf",
        "timesi.ttf", "LiberationSerif-Italic.ttf", "DejaVuSerif-Oblique.ttf",
    ],
    "display_regular": [
        # Playfair Display: high-contrast display serif — headings
        "PlayfairDisplay[wght].ttf", "PlayfairDisplay-Regular.ttf",
        "georgia.ttf", "times.ttf", "LiberationSerif-Regular.ttf",
    ],
    "display_bold": [
        "PlayfairDisplay[wght].ttf", "PlayfairDisplay-Bold.ttf",
        "georgiab.ttf", "timesbd.ttf", "LiberationSerif-Bold.ttf",
    ],
    "display_italic": [
        "PlayfairDisplay-Italic[wght].ttf", "PlayfairDisplay-Italic.ttf",
        "timesi.ttf", "LiberationSerif-Italic.ttf",
    ],
    "blackletter": [
        # UnifrakturMaguntia: Old-English blackletter — dramatic title banner
        "UnifrakturMaguntia-Book.ttf", "UnifrakturMaguntia.ttf",
        # Fallbacks (no blackletter on standard Linux, so use Cinzel then Times)
        "Cinzel[wght].ttf", "Cinzel-Bold.ttf", "georgiab.ttf", "timesbd.ttf",
        "LiberationSerif-Bold.ttf",
    ],
    # ── Standard serif / sans (unchanged) ─────────────────────────────────────
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


# ── 5 script style keys (randomly picked per cert) ───────────────────────────
_SCRIPT_STYLES = ["script", "script_parisienne", "script_allura", "script_pinyon", "script_alex"]


def get_fonts(scale: float = 1.0, script_style: Optional[str] = None) -> Dict[str, ImageFont.ImageFont]:
    """Return a dict of named font variants scaled by *scale*.

    Parameters
    ----------
    scale        : overall size multiplier (default 1.0)
    script_style : one of the 5 script style keys to use for student name.
                   If None, a random script is chosen each call — produces
                   5x more cursive variety across generated certificates.

    Keys (original)
    ---------------
    title, subtitle, heading, body, body_italic,
    label, value, small, geo_title, geo_body, calibri.

    Keys (calligraphy / formal)
    ---------------------------
    script       — random from: Great Vibes, Parisienne, Allura, Pinyon, Alex Brush
    script_sm    — same font at smaller size
    cinzel       — Cinzel engraved bold (university name / title)
    cinzel_sm    — Cinzel regular (smaller institution labels)
    antique      — IM Fell English regular (body prose)
    antique_it   — IM Fell English italic (proclamation lines)
    display      — Playfair Display bold (section headings)
    display_it   — Playfair Display italic (sub-headings)
    blackletter  — UnifrakturMaguntia (optional dramatic banner)
    """
    import random as _random
    base = int(26 * scale)
    # Pick one of 5 script styles randomly if not specified
    chosen_script = script_style or _random.choice(_SCRIPT_STYLES)
    return {
        # ── Original slots (unchanged — existing templates still work) ─────────
        "title":        _load("serif_bold",      int(base * 1.70)),
        "subtitle":     _load("serif_bold",      int(base * 1.15)),
        "heading":      _load("serif_bold",      int(base * 0.95)),
        "body":         _load("serif_regular",   int(base * 0.88)),
        "body_italic":  _load("serif_italic",    int(base * 0.88)),
        "label":        _load("sans_bold",       int(base * 0.72)),
        "value":        _load("sans_regular",    int(base * 0.80)),
        "small":        _load("serif_regular",   int(base * 0.65)),
        "geo_title":    _load("georgia_bold",    int(base * 1.55)),
        "geo_body":     _load("georgia_regular", int(base * 0.88)),
        "calibri":      _load("calibri",         int(base * 0.85)),
        # ── Calligraphy / formal slots ──────────────────────────────────────────
        # Randomly chosen from 5 OFL scripts — each cert looks different!
        "script":       _load(chosen_script,     int(base * 2.00)),
        "script_sm":    _load(chosen_script,     int(base * 1.40)),
        # university name / title in engraved Roman capitals
        "cinzel":       _load("cinzel_bold",     int(base * 1.20)),
        "cinzel_sm":    _load("cinzel_regular",  int(base * 0.80)),
        # antique book type for body prose (IM Fell English)
        "antique":      _load("antique_regular", int(base * 0.90)),
        "antique_it":   _load("antique_italic",  int(base * 0.90)),
        # Playfair Display for headings
        "display":      _load("display_bold",    int(base * 1.05)),
        "display_it":   _load("display_italic",  int(base * 0.90)),
        # Old-English blackletter for dramatic title banners
        "blackletter":  _load("blackletter",     int(base * 1.30)),
    }


__all__ = ["get_fonts", "download_certificate_fonts"]
