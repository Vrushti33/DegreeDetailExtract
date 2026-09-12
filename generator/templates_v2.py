"""Six new Pillow certificate templates (t23–t28) that use:

1. Real paper background textures via ``realistic_bg.sample_background()``.
2. Full ceremonial prose text via ``prose.get_random_prose()``.

These templates require the ``BG_POOL`` module-level variable to be
initialised before generation begins (done by ``renderer_v2.py``).

All templates share the same 1000 × 1400 px canvas as the existing ones
so they are fully compatible with the Donut processor's image resizer.
"""

from __future__ import annotations

import random
from typing import List, Optional, TYPE_CHECKING

from PIL import Image, ImageDraw

from .fonts import get_fonts
from .templates import (  # reuse all drawing utilities from existing module
    W, H, TEXT_BLACK, TEXT_DARK, TEXT_WHITE, TEXT_NAVY, TEXT_GREEN,
    TEXT_DARK_RED, GOLD, BRIGHT_GOLD, WARM_GOLD, DARK_GOLD,
    NAVY, DARK_NAVY, BURGUNDY, DARK_GREEN, CHARCOAL, DARK_BLUE, SLATE,
    CREAM, PARCHMENT, OLD_LACE, IVORY, WHITE, LIGHT_GREY,
    LIGHT_BLUE, LIGHT_GREEN, LIGHT_YELLOW,
    BROWN, GOLDEN_BROWN,
    draw_centered, draw_centered_wrapped, wrap_text,
    hline, double_hline, _tw, _th,
)
from .prose import get_random_prose

# ── module-level pool — set by renderer_v2 before first call ──────────────────
BG_POOL: List = []   # list[CertTexture] from realistic_bg

# ── import sampler lazily so this module doesn't fail without OpenCV ──────────
def _sample_bg(base_color):
    try:
        from .realistic_bg import sample_background
        return sample_background(BG_POOL, target_size=(W, H), base_color=base_color)
    except Exception:
        return Image.new("RGB", (W, H), base_color)


def _sample_ink():
    try:
        from .realistic_bg import sample_ink_color
        c = sample_ink_color(BG_POOL)
        # Ensure ink is dark enough to be readable
        if sum(c) > 400:
            return (20, 20, 20)
        return c
    except Exception:
        return (20, 20, 20)


# ──────────────────────────────────────────────────────────────────────────────
#  Shared prose renderer
# ──────────────────────────────────────────────────────────────────────────────

def _render_prose_body(draw, fonts, fields, y_start, ink, margin=80) -> int:
    """Render the full ceremonial prose into the image. Returns y after last line."""
    prose = get_random_prose(fields)
    y = y_start
    max_w = W - margin * 2

    # Header lines (already drawn by templates above, but some prose has extra)
    # Proclamation paragraph
    if prose.proclamation:
        y = draw_centered_wrapped(draw, prose.proclamation, y, fonts["body_italic"], ink, max_w, spacing=6)
        y += 14

    # Recipient label
    if prose.recipient_label:
        draw_centered(draw, prose.recipient_label.upper(), y, fonts["label"], ink)
        y += 36

    # Body paragraphs
    for para in prose.body_paragraphs:
        for line in para.split("\n"):
            line = line.strip()
            if not line:
                y += 10
                continue
            y = draw_centered_wrapped(draw, line, y, fonts["body"], ink, max_w, spacing=5)
            y += 10

    y += 8
    # Award line
    if prose.award_line:
        hline(draw, y, ink, width=1, margin=margin + 40)
        y += 14
        draw_centered(draw, prose.award_line.upper(), y, fonts["heading"], ink)
        y += 42

    # Closing lines
    if prose.closing_lines:
        hline(draw, y, ink, width=1, margin=margin + 40)
        y += 14
        for cl in prose.closing_lines:
            y = draw_centered_wrapped(draw, cl, y, fonts["small"], ink, max_w, spacing=4)
            y += 6

    return y


# ══════════════════════════════════════════════════════════════════════════════
#  Template 23 — Real-texture Parchment Prose
# ══════════════════════════════════════════════════════════════════════════════
def t23_texture_parchment_prose(fields: dict) -> Image.Image:
    """Real paper texture background + ceremonial prose, classic parchment style."""
    BORDER = (139, 69, 19)
    base   = (253, 245, 220)
    ink    = _sample_ink() or (80, 40, 10)

    img  = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Ornate double border
    draw.rectangle([14, 14, W - 14, H - 14], outline=BORDER, width=4)
    draw.rectangle([28, 28, W - 28, H - 28], outline=GOLDEN_BROWN, width=1)
    for cx, cy in [(14, 14), (W - 14, 14), (14, H - 14), (W - 14, H - 14)]:
        draw.polygon([(cx, cy - 12), (cx + 12, cy), (cx, cy + 12), (cx - 12, cy)], fill=BORDER)

    y = 60
    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["title"], W - 140):
        y += draw_centered(draw, ln, y, fonts["title"], BORDER) + 6
    y += 8
    double_hline(draw, y, BORDER, gap=6, w1=3, w2=1, margin=60)
    y += 28
    draw_centered(draw, "OFFICIAL DEGREE CERTIFICATE", y, fonts["heading"], GOLDEN_BROWN)
    y += 50

    y = _render_prose_body(draw, fonts, fields, y, ink, margin=70)

    # Signature block at bottom
    fy = H - 155
    double_hline(draw, fy, BORDER, gap=6, w1=2, w2=1, margin=70)
    draw.text((90, fy + 20), "Signed by:", font=fonts["small"], fill=BORDER)
    draw.text((90, fy + 42), fields["authority_name"], font=fonts["body"], fill=ink)
    ds = f"Date: {fields['issue_date']}"
    draw.text((W - 90 - _tw(draw, ds, fonts["body"]), fy + 42), ds, font=fonts["body"], fill=ink)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 24 — Real-texture Navy Prose
# ══════════════════════════════════════════════════════════════════════════════
def t24_texture_navy_prose(fields: dict) -> Image.Image:
    """Real paper texture with navy header/footer bands + full prose body."""
    base = (248, 250, 255)
    ink  = _sample_ink() or (20, 20, 60)

    img  = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Navy header band
    draw.rectangle([0, 0, W, 170], fill=NAVY)
    draw.line([(0, 170), (W, 170)], fill=BRIGHT_GOLD, width=3)
    draw.rectangle([0, H - 70, W, H], fill=DARK_NAVY)
    draw.line([(0, H - 70), (W, H - 70)], fill=BRIGHT_GOLD, width=2)

    y = 26
    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["subtitle"], W - 100):
        y += draw_centered(draw, ln, y, fonts["subtitle"], TEXT_WHITE) + 5
    draw_centered(draw, "DEGREE CERTIFICATE", y, fonts["heading"], BRIGHT_GOLD)
    y = 192

    y = _render_prose_body(draw, fonts, fields, y, ink, margin=80)

    # Footer
    draw.text((80, H - 52), fields["authority_name"], font=fonts["small"], fill=TEXT_WHITE)
    ds = f"Issued: {fields['issue_date']}"
    draw.text((W - 80 - _tw(draw, ds, fonts["small"]), H - 52), ds, font=fonts["small"], fill=TEXT_WHITE)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 25 — Real-texture Burgundy Prose
# ══════════════════════════════════════════════════════════════════════════════
def t25_texture_burgundy_prose(fields: dict) -> Image.Image:
    """Real paper background + burgundy border + ceremonial proclamation style."""
    base = (255, 252, 248)
    ink  = _sample_ink() or (80, 10, 30)

    img  = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([16, 16, W - 16, H - 16], outline=BURGUNDY, width=5)
    draw.rectangle([30, 30, W - 30, H - 30], outline=GOLDEN_BROWN, width=1)
    for cx, cy in [(16, 16), (W - 16, 16), (16, H - 16), (W - 16, H - 16)]:
        draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=BURGUNDY)

    y = 60
    draw_centered(draw, "UNIVERSITY DEGREE CERTIFICATE", y, fonts["heading"], GOLDEN_BROWN)
    y += 42
    double_hline(draw, y, BURGUNDY, gap=7, w1=3, w2=1, margin=60)
    y += 28

    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["title"], W - 130):
        y += draw_centered(draw, ln, y, fonts["title"], BURGUNDY) + 6
    y += 16
    double_hline(draw, y, BURGUNDY, gap=7, w1=3, w2=1, margin=60)
    y += 30

    y = _render_prose_body(draw, fonts, fields, y, ink, margin=72)

    # Seal circle
    cx, cy, r = W - 120, H - 110, 58
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=BURGUNDY, width=3)
    draw.ellipse([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8], outline=GOLDEN_BROWN, width=1)
    draw_centered(draw, "SEAL", cy - 8, fonts["small"], BURGUNDY)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 26 — Real-texture Dark Elegant Prose
# ══════════════════════════════════════════════════════════════════════════════
def t26_texture_dark_elegant(fields: dict) -> Image.Image:
    """Dark navy near-solid background (like premium printed certificate) + gold prose."""
    # For dark templates blend very lightly so background stays legible
    base = (18, 40, 70)
    ink  = (230, 195, 60)   # gold on dark

    img  = _sample_bg(base_color=base)
    # Darken heavily so real texture is subtle
    dark_overlay = Image.new("RGBA", (W, H), (15, 35, 65, 220))
    img = Image.alpha_composite(img.convert("RGBA"), dark_overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Gold border
    draw.rectangle([18, 18, W - 18, H - 18], outline=BRIGHT_GOLD, width=3)
    draw.rectangle([28, 28, W - 28, H - 28], outline=(160, 120, 20), width=1)

    y = 58
    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["subtitle"], W - 120):
        y += draw_centered(draw, ln, y, fonts["subtitle"], BRIGHT_GOLD) + 6
    y += 10
    hline(draw, y, BRIGHT_GOLD, width=2, margin=80)
    y += 24
    draw_centered(draw, "DEGREE CERTIFICATE", y, fonts["heading"], TEXT_WHITE)
    y += 52

    y = _render_prose_body(draw, fonts, fields, y, TEXT_WHITE, margin=80)

    # Signature
    fy = H - 140
    hline(draw, fy, BRIGHT_GOLD, width=1, margin=80)
    draw.text((90, fy + 18), fields["authority_name"], font=fonts["body"], fill=BRIGHT_GOLD)
    ds = f"Date: {fields['issue_date']}"
    draw.text((W - 90 - _tw(draw, ds, fonts["body"]), fy + 18), ds, font=fonts["body"], fill=BRIGHT_GOLD)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 27 — Real-texture Cream Multi-column Prose
# ══════════════════════════════════════════════════════════════════════════════
def t27_texture_cream_multicolumn(fields: dict) -> Image.Image:
    """Cream/ivory background with two decorative side panels + prose body."""
    base  = (253, 250, 235)
    PANEL = (240, 230, 200)
    ACCENT = (100, 60, 15)
    ink   = _sample_ink() or ACCENT

    img  = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Side decorative panels
    draw.rectangle([0, 0, 55, H], fill=PANEL)
    draw.rectangle([W - 55, 0, W, H], fill=PANEL)
    draw.line([(55, 0), (55, H)], fill=ACCENT, width=2)
    draw.line([(W - 55, 0), (W - 55, H)], fill=ACCENT, width=2)

    # Header
    y = 50
    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["title"], W - 200):
        y += draw_centered(draw, ln, y, fonts["title"], ACCENT) + 6
    y += 6
    hline(draw, y, ACCENT, width=2, margin=80)
    y += 20
    draw_centered(draw, "CERTIFICATE OF DEGREE", y, fonts["heading"], GOLDEN_BROWN)
    y += 50

    y = _render_prose_body(draw, fonts, fields, y, ink, margin=80)

    # Bottom signature inside panels
    fy = H - 145
    hline(draw, fy, ACCENT, width=1, margin=80)
    draw.text((80, fy + 18), "Authorised by:", font=fonts["small"], fill=ACCENT)
    draw.text((80, fy + 40), fields["authority_name"], font=fonts["body"], fill=ink)
    ds = f"Issued: {fields['issue_date']}"
    draw.text((W - 90 - _tw(draw, ds, fonts["body"]), fy + 40), ds, font=fonts["body"], fill=ink)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 28 — Real-texture Minimal Clean Prose
# ══════════════════════════════════════════════════════════════════════════════
def t28_texture_minimal_clean(fields: dict) -> Image.Image:
    """Subtle real texture on near-white background, thin line borders, plain prose."""
    base = (252, 252, 252)
    ink  = _sample_ink() or (30, 30, 30)
    ACCENT = (80, 100, 120)

    img  = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Thin border lines
    draw.rectangle([20, 20, W - 20, H - 20], outline=ACCENT, width=1)
    draw.line([(40, 80), (W - 40, 80)], fill=ACCENT, width=1)

    y = 36
    for ln in wrap_text(draw, fields["university_name"], fonts["subtitle"], W - 160):
        y += draw_centered(draw, ln, y, fonts["subtitle"], SLATE) + 5
    y += 6
    draw.line([(40, y), (W - 40, y)], fill=ACCENT, width=1)
    y += 26
    draw_centered(draw, "DEGREE CERTIFICATE", y, fonts["heading"], (50, 50, 60))
    y += 52

    y = _render_prose_body(draw, fonts, fields, y, ink, margin=80)

    # Minimal signature
    fy = H - 130
    draw.line([(60, fy), (W - 60, fy)], fill=ACCENT, width=1)
    draw.text((80, fy + 16), fields["authority_name"], font=fonts["body"], fill=ink)
    ds = f"Date: {fields['issue_date']}"
    draw.text((W - 80 - _tw(draw, ds, fonts["body"]), fy + 16), ds, font=fonts["body"], fill=ink)

    return img


# ── Template list exported by this module ─────────────────────────────────────
TEMPLATES_V2 = [
    t23_texture_parchment_prose,
    t24_texture_navy_prose,
    t25_texture_burgundy_prose,
    t26_texture_dark_elegant,
    t27_texture_cream_multicolumn,
    t28_texture_minimal_clean,
]

__all__ = ["TEMPLATES_V2", "BG_POOL"]
