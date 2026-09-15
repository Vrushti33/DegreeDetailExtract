"""Eight new certificate templates (t29–t36) — v3 anti-overfitting upgrade.

Each template addresses one or more gaps identified in v2:
  t29  Fully-cursive body     — IM Fell / Great Vibes for ALL body text
  t30  Name-at-top banner     — student name in large script above all prose
  t31  Label-value grid       — structured printed rows, South-Asian style
  t32  Gothic blackletter     — UnifrakturMaguntia title + antique body
  t33  Sepia worn document    — aged paper texture, sepia ink, worn feel
  t34  Double-border vintage  — heavy double border + parchment, name centred
  t35  Full-page watermark    — translucent seal ring behind text
  t36  Wide-margin formal     — wide left margin with decorative rule, clean body

All templates:
  • Use real paper backgrounds via realistic_bg when available
  • Render full prose through prose.get_random_prose()
  • Handle pass_class being empty (no award line if absent)
  • Vary student name placement (top / inline / centred standalone)
"""

from __future__ import annotations

import random
from typing import List

from PIL import Image, ImageDraw

from .fonts import get_fonts
from .templates import (
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

# ── module-level pool — set by renderer_v3 ───────────────────────────────────
BG_POOL: List = []


def _sample_bg(base_color):
    try:
        from .realistic_bg import sample_background
        return sample_background(BG_POOL, target_size=(W, H), base_color=base_color)
    except Exception:
        return Image.new("RGB", (W, H), base_color)


def _sample_ink(fallback=(30, 20, 10)):
    try:
        from .realistic_bg import sample_ink_color
        c = sample_ink_color(BG_POOL)
        if sum(c) > 420:
            return fallback
        return c
    except Exception:
        return fallback


# ── Shared prose renderer (v3 extended) ──────────────────────────────────────

def _render_prose_body_v3(draw, fonts, fields, prose, y_start, ink,
                           margin=80, line_spacing=1.0) -> int:
    """Render the prose blocks. Handles name_at_top, all_cursive, absent pass_class.

    Parameters
    ----------
    line_spacing : float  Extra multiplier on line height (1.0–1.8 for real cert feel)
    """
    max_w = W - margin * 2
    y = y_start

    # Font selection
    proc_font    = fonts.get("antique_it")  or fonts["body_italic"]
    body_font    = fonts.get("antique")     or fonts["body"]
    award_font   = fonts.get("display")     or fonts["heading"]
    script_font  = fonts.get("script")      or fonts.get("geo_title") or fonts["title"]
    cinzel_font  = fonts.get("cinzel")      or fonts["title"]

    # all_cursive: replace body_font with script/antique italic
    if prose.all_cursive:
        body_font  = fonts.get("antique_it") or fonts.get("antique") or fonts["body_italic"]
        proc_font  = body_font

    sp = int(12 * line_spacing)   # paragraph spacing

    # name_at_top: render student name first in large script
    if prose.name_at_top:
        y += 10
        h = draw_centered(draw, fields["student_name"], y, script_font, ink)
        y += h + int(28 * line_spacing)
        nw = _tw(draw, fields["student_name"], script_font)
        draw.line([(W // 2 - nw // 2, y), (W // 2 + nw // 2, y)], fill=ink, width=1)
        y += 18

    # Proclamation
    if prose.proclamation:
        y = draw_centered_wrapped(draw, prose.proclamation, y, proc_font, ink, max_w, spacing=5)
        y += int(14 * line_spacing)

    # Recipient label
    if prose.recipient_label:
        draw_centered(draw, prose.recipient_label.upper(), y, fonts["label"], ink)
        y += int(36 * line_spacing)

    # Body paragraphs
    for para in prose.body_paragraphs:
        p_clean = para.strip()

        # Standalone student name → render in script font, centred with extra space
        if not prose.name_at_top and p_clean == fields["student_name"].strip():
            y += int(8 * line_spacing)
            h = draw_centered(draw, p_clean, y, script_font, ink)
            y += h + int(24 * line_spacing)
            continue

        # Label-value block: left-aligned
        if "\n" in para or para.startswith("Name of") or para.startswith("Degree") \
                or para.startswith("Specialization") or para.startswith("University") \
                or para.startswith("Date") or para.startswith("Class") \
                or para.startswith("Authorised") or para.startswith("Result"):
            for ln in para.split("\n"):
                ln = ln.strip()
                if ln:
                    lw = _tw(draw, ln, body_font)
                    draw.text(((W - lw) // 2, y), ln, font=body_font, fill=ink)
                    y += _th(draw, ln, body_font) + int(6 * line_spacing)
            y += int(sp // 2)
            continue

        # Normal wrapped paragraph
        for line in para.split("\n"):
            line = line.strip()
            if not line:
                y += int(8 * line_spacing)
                continue
            y = draw_centered_wrapped(draw, line, y, body_font, ink, max_w, spacing=4)
            y += int(8 * line_spacing)
        y += sp

    y += 6
    # Award line (omit if empty)
    if prose.award_line:
        hline(draw, y, ink, width=1, margin=margin + 40)
        y += 12
        draw_centered(draw, prose.award_line.upper(), y, award_font, ink)
        y += int(40 * line_spacing)

    # Closing lines
    if prose.closing_lines:
        hline(draw, y, ink, width=1, margin=margin + 40)
        y += 12
        for cl in prose.closing_lines:
            y = draw_centered_wrapped(draw, cl, y, fonts["small"], ink, max_w, spacing=3)
            y += int(6 * line_spacing)

    return y


# ══════════════════════════════════════════════════════════════════════════════
#  Template 29 — Fully-cursive / script body
# ══════════════════════════════════════════════════════════════════════════════
def t29_fully_cursive_parchment(fields: dict) -> Image.Image:
    """Entire body rendered in IM Fell English Italic (antique cursive).
    Simulates copper-plate printed old-style diplomas."""
    base = (252, 246, 228)
    ink  = _sample_ink((60, 40, 10))
    BORDER = (120, 80, 20)

    img  = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Decorative border
    draw.rectangle([16, 16, W - 16, H - 16], outline=BORDER, width=3)
    draw.rectangle([26, 26, W - 26, H - 26], outline=GOLDEN_BROWN, width=1)
    draw.rectangle([30, 30, W - 30, H - 30], outline=BORDER, width=1)

    y = 50
    # University in Cinzel engraved caps
    cinzel = fonts.get("cinzel") or fonts["title"]
    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 140):
        y += draw_centered(draw, ln, y, cinzel, BORDER) + 5
    y += 8
    hline(draw, y, BORDER, width=2, margin=60)
    y += 16
    # Sub-title in Playfair italic
    disp = fonts.get("display_it") or fonts.get("display") or fonts["heading"]
    draw_centered(draw, "Certificate of Degree", y, disp, GOLDEN_BROWN)
    y += 48

    prose = get_random_prose(fields)
    # Force all_cursive
    from .prose import ProseBlocks
    prose = ProseBlocks(
        header_lines=prose.header_lines,
        proclamation=prose.proclamation,
        recipient_label=prose.recipient_label,
        body_paragraphs=prose.body_paragraphs,
        award_line=prose.award_line,
        closing_lines=prose.closing_lines,
        all_cursive=True,
        name_at_top=prose.name_at_top,
    )

    spacing = random.uniform(1.1, 1.5)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=65, line_spacing=spacing)

    # Signature
    fy = H - 140
    hline(draw, fy, BORDER, width=1, margin=65)
    draw.text((80, fy + 18), fields["authority_name"], font=fonts["small"], fill=ink)
    ds = f"Date: {fields['issue_date']}"
    draw.text((W - 80 - _tw(draw, ds, fonts["small"]), fy + 18), ds, font=fonts["small"], fill=ink)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 30 — Name-at-top banner
# ══════════════════════════════════════════════════════════════════════════════
def t30_name_at_top_banner(fields: dict) -> Image.Image:
    """Student name prominently centred at the top in large script calligraphy,
    followed by formal prose body. Common in Australian/European diplomas."""
    base = (253, 250, 242)
    ink  = _sample_ink((30, 30, 50))
    ACCENT = NAVY

    img  = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Header band
    draw.rectangle([0, 0, W, 80], fill=ACCENT)
    draw.line([(0, 80), (W, 80)], fill=BRIGHT_GOLD, width=3)

    y = 14
    cinzel = fonts.get("cinzel") or fonts["subtitle"]
    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 80):
        y += draw_centered(draw, ln, y, cinzel, TEXT_WHITE) + 4

    y = 110
    # Big script name
    script = fonts.get("script") or fonts["geo_title"]
    h = draw_centered(draw, fields["student_name"], y, script, ACCENT)
    y += h + 10
    nw = _tw(draw, fields["student_name"], script)
    draw.line([(W // 2 - nw // 2, y), (W // 2 + nw // 2, y)], fill=BRIGHT_GOLD, width=2)
    y += 22
    draw.line([(W // 2 - nw // 2 + 14, y), (W // 2 + nw // 2 - 14, y)], fill=ACCENT, width=1)
    y += 22

    prose = get_random_prose(fields)
    from .prose import ProseBlocks
    prose = ProseBlocks(
        header_lines=prose.header_lines,
        proclamation=prose.proclamation,
        recipient_label=prose.recipient_label,
        body_paragraphs=prose.body_paragraphs,
        award_line=prose.award_line,
        closing_lines=prose.closing_lines,
        name_at_top=True,        # skip name rendering inside body
        all_cursive=False,
    )

    spacing = random.uniform(1.0, 1.4)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=75, line_spacing=spacing)

    # Footer band
    draw.rectangle([0, H - 70, W, H], fill=DARK_NAVY)
    draw.text((80, H - 48), fields["authority_name"], font=fonts["small"], fill=TEXT_WHITE)
    ds = f"Issued: {fields['issue_date']}"
    draw.text((W - 80 - _tw(draw, ds, fonts["small"]), H - 48), ds, font=fonts["small"], fill=TEXT_WHITE)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 31 — Label-value grid (South-Asian printed style)
# ══════════════════════════════════════════════════════════════════════════════
def t31_label_value_grid(fields: dict) -> Image.Image:
    """Structured label:value rows. The most common format on Indian university
    printed degree certificates (Andhra, Osmania, Mumbai, etc.)."""
    base = (255, 254, 248)
    ink  = _sample_ink((20, 20, 20))
    ACCENT = (30, 60, 100)

    img  = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Top border
    draw.rectangle([0, 0, W, 10], fill=ACCENT)
    draw.rectangle([0, H - 10, W, H], fill=ACCENT)
    draw.rectangle([18, 18, W - 18, H - 18], outline=ACCENT, width=2)

    y = 45
    cinzel = fonts.get("cinzel") or fonts["title"]
    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 120):
        y += draw_centered(draw, ln, y, cinzel, ACCENT) + 5
    hline(draw, y, ACCENT, width=2, margin=60)
    y += 14
    draw_centered(draw, "DEGREE CERTIFICATE", y, fonts["heading"], ACCENT)
    y += 42
    hline(draw, y, ACCENT, width=1, margin=60)
    y += 24

    # Proclamation
    proc = fonts.get("antique_it") or fonts["body_italic"]
    y = draw_centered_wrapped(
        draw,
        "This is to certify that the candidate whose particulars are given below "
        "has been duly awarded the degree as mentioned hereunder:",
        y, proc, ink, W - 160, spacing=5)
    y += 20

    # Label-value rows
    lv_pairs = [
        ("Name of Candidate", fields["student_name"]),
        ("University",        fields["university_name"]),
        ("Degree Awarded",    fields["course_name"]),
        ("Specialization",    fields["specialization"]),
        ("Date of Award",     fields["issue_date"]),
    ]
    if fields.get("pass_class"):
        lv_pairs.append(("Class / Division", fields["pass_class"]))
    lv_pairs.append(("Authorised By", fields["authority_name"]))

    lbl_font = fonts["label"]
    val_font = fonts.get("antique") or fonts["body"]
    script   = fonts.get("script")  or fonts["geo_title"]

    left = 90
    colon_x = 340
    val_x   = 360

    for label, value in lv_pairs:
        draw.text((left, y), label, font=lbl_font, fill=ACCENT)
        draw.text((colon_x, y), ":", font=lbl_font, fill=ACCENT)
        # Student name in script font
        use_font = script if label == "Name of Candidate" else val_font
        lines = wrap_text(draw, value, use_font, W - val_x - 60)
        for ln in lines:
            draw.text((val_x, y), ln, font=use_font, fill=ink)
            y += _th(draw, ln, use_font) + 6
        y += 8

    hline(draw, y + 10, ACCENT, width=1, margin=60)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 32 — Gothic / Old-English blackletter
# ══════════════════════════════════════════════════════════════════════════════
def t32_gothic_blackletter(fields: dict) -> Image.Image:
    """Dramatic Old-English blackletter title band with antique body prose.
    Common in old European and some residential Indian university diplomas."""
    base  = (252, 248, 235)
    ink   = _sample_ink((40, 20, 10))
    DEEP  = (60, 10, 10)

    img  = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Triple-line borders
    for off, w in [(12, 4), (22, 1), (26, 2)]:
        draw.rectangle([off, off, W - off, H - off], outline=DEEP, width=w)

    y = 46
    # BlackLetter title
    bl_font = fonts.get("blackletter") or fonts["title"]
    for ln in wrap_text(draw, fields["university_name"], bl_font, W - 130):
        y += draw_centered(draw, ln, y, bl_font, DEEP) + 5
    y += 6
    hline(draw, y, DEEP, width=2, margin=55)
    hline(draw, y + 6, GOLDEN_BROWN, width=1, margin=55)
    y += 24

    # Sub-title in Cinzel
    cinzel = fonts.get("cinzel") or fonts["subtitle"]
    draw_centered(draw, "BE IT KNOWN TO ALL THAT", y, cinzel, GOLDEN_BROWN)
    y += 40

    prose = get_random_prose(fields)
    spacing = random.uniform(1.1, 1.5)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=70, line_spacing=spacing)

    fy = H - 135
    hline(draw, fy, DEEP, width=1, margin=70)
    draw.text((85, fy + 16), fields["authority_name"], font=fonts["small"], fill=ink)
    ds = f"Sealed on: {fields['issue_date']}"
    draw.text((W - 85 - _tw(draw, ds, fonts["small"]), fy + 16), ds, font=fonts["small"], fill=ink)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 33 — Sepia / aged worn document
# ══════════════════════════════════════════════════════════════════════════════
def t33_sepia_worn_document(fields: dict) -> Image.Image:
    """Aged sepia-toned document. Real texture blended with sepia overlay.
    Mimics old scanned degree certificates from the 1970s–90s."""
    base = (240, 220, 175)   # warm sepia base
    ink  = (55, 35, 10)

    img  = _sample_bg(base_color=base)
    # Sepia overlay
    sepia = Image.new("RGBA", (W, H), (120, 80, 30, 60))
    img = Image.alpha_composite(img.convert("RGBA"), sepia).convert("RGB")
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    BORDER = (90, 55, 20)
    draw.rectangle([14, 14, W - 14, H - 14], outline=BORDER, width=3)
    draw.rectangle([24, 24, W - 24, H - 24], outline=(150, 100, 40), width=1)

    y = 52
    cinzel = fonts.get("cinzel") or fonts["title"]
    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 140):
        y += draw_centered(draw, ln, y, cinzel, BORDER) + 5
    y += 8
    double_hline(draw, y, BORDER, gap=5, w1=2, w2=1, margin=60)
    y += 20

    disp = fonts.get("display") or fonts["heading"]
    draw_centered(draw, "CERTIFICATE OF DEGREE", y, disp, (110, 70, 25))
    y += 48

    prose = get_random_prose(fields)
    spacing = random.uniform(1.2, 1.7)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=70, line_spacing=spacing)

    fy = H - 140
    hline(draw, fy, BORDER, width=1, margin=70)
    draw.text((85, fy + 18), fields["authority_name"], font=fonts["small"], fill=ink)
    ds = f"Date: {fields['issue_date']}"
    draw.text((W - 85 - _tw(draw, ds, fonts["small"]), fy + 18), ds, font=fonts["small"], fill=ink)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 34 — Double-border vintage (name centred standalone)
# ══════════════════════════════════════════════════════════════════════════════
def t34_double_border_vintage(fields: dict) -> Image.Image:
    """Heavy double border + parchment, student name centred standalone in the
    middle of the certificate (common in UK/Australian graduation diplomas)."""
    base   = PARCHMENT
    ink    = _sample_ink((50, 30, 10))
    BORDER = (120, 70, 15)
    GOLD   = (180, 140, 30)

    img  = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Heavy double border + corner ornaments
    draw.rectangle([12, 12, W - 12, H - 12], outline=BORDER, width=5)
    draw.rectangle([26, 26, W - 26, H - 26], outline=GOLD, width=2)
    draw.rectangle([34, 34, W - 34, H - 34], outline=BORDER, width=1)
    for cx, cy in [(12, 12), (W - 12, 12), (12, H - 12), (W - 12, H - 12)]:
        draw.rectangle([cx - 8, cy - 8, cx + 8, cy + 8], fill=BORDER)
        draw.rectangle([cx - 4, cy - 4, cx + 4, cy + 4], fill=GOLD)

    y = 58
    cinzel = fonts.get("cinzel") or fonts["title"]
    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 150):
        y += draw_centered(draw, ln, y, cinzel, BORDER) + 5
    y += 8
    double_hline(draw, y, BORDER, gap=7, w1=3, w2=1, margin=55)
    y += 22
    disp = fonts.get("display") or fonts["heading"]
    draw_centered(draw, "DEGREE CERTIFICATE", y, disp, GOLD)
    y += 50

    # Proclamation
    prose = get_random_prose(fields)
    body_f = fonts.get("antique") or fonts["body"]
    proc_f = fonts.get("antique_it") or fonts["body_italic"]

    if prose.proclamation:
        y = draw_centered_wrapped(draw, prose.proclamation, y, proc_f, ink, W - 160, spacing=5)
        y += 16
    if prose.recipient_label:
        draw_centered(draw, prose.recipient_label.upper(), y, fonts["label"], ink)
        y += 34

    # Student name centred standalone in script
    y += 16
    script = fonts.get("script") or fonts["geo_title"]
    h = draw_centered(draw, fields["student_name"], y, script, BORDER)
    y += h + 10
    nw = _tw(draw, fields["student_name"], script)
    draw.line([(W // 2 - nw // 2, y), (W // 2 + nw // 2, y)], fill=GOLD, width=2)
    y += 28

    # Rest of prose body
    for para in prose.body_paragraphs:
        if para.strip() == fields["student_name"].strip():
            continue  # already rendered above
        y = draw_centered_wrapped(draw, para, y, body_f, ink, W - 160, spacing=4)
        y += int(10 * random.uniform(1.0, 1.5))

    if prose.award_line:
        hline(draw, y, BORDER, width=1, margin=110)
        y += 12
        draw_centered(draw, prose.award_line.upper(), y, disp, GOLD)
        y += 38

    if prose.closing_lines:
        hline(draw, y, BORDER, width=1, margin=110)
        y += 12
        for cl in prose.closing_lines:
            y = draw_centered_wrapped(draw, cl, y, fonts["small"], ink, W - 160, spacing=3)
            y += 6

    fy = H - 130
    draw.text((75, fy), fields["authority_name"], font=fonts["small"], fill=ink)
    ds = f"Date: {fields['issue_date']}"
    draw.text((W - 75 - _tw(draw, ds, fonts["small"]), fy), ds, font=fonts["small"], fill=ink)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 35 — Full-page seal watermark behind text
# ══════════════════════════════════════════════════════════════════════════════
def t35_watermark_seal(fields: dict) -> Image.Image:
    """Large translucent seal ring drawn behind all text.
    Simulates embossed or printed university seals common on real degrees."""
    base = (253, 251, 244)
    ink  = _sample_ink((25, 25, 45))
    ACCENT = (40, 60, 100)

    img  = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Watermark seal (large circle at centre)
    cx, cy, r = W // 2, H // 2, 280
    wm_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wm_draw = ImageDraw.Draw(wm_overlay)
    wm_draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(60, 80, 140, 55), width=6)
    wm_draw.ellipse([cx - r + 20, cy - r + 20, cx + r - 20, cy + r - 20],
                    outline=(60, 80, 140, 40), width=3)
    cinzel_wm = fonts.get("cinzel") or fonts["small"]
    # University name arc simulation: just draw horizontally across seal centre
    univ_text = fields["university_name"].upper()[:30]
    uw = _tw(wm_draw, univ_text, cinzel_wm)
    wm_draw.text(((W - uw) // 2, cy - 18), univ_text, font=cinzel_wm, fill=(60, 80, 140, 50))
    img = Image.alpha_composite(img.convert("RGBA"), wm_overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Thin border
    draw.rectangle([16, 16, W - 16, H - 16], outline=ACCENT, width=2)

    y = 42
    cinzel = fonts.get("cinzel") or fonts["title"]
    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 120):
        y += draw_centered(draw, ln, y, cinzel, ACCENT) + 5
    hline(draw, y, ACCENT, width=2, margin=70)
    y += 16
    disp = fonts.get("display") or fonts["heading"]
    draw_centered(draw, "DEGREE CERTIFICATE", y, disp, ACCENT)
    y += 50

    prose = get_random_prose(fields)
    spacing = random.uniform(1.15, 1.6)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=80, line_spacing=spacing)

    fy = H - 130
    hline(draw, fy, ACCENT, width=1, margin=80)
    draw.text((85, fy + 16), fields["authority_name"], font=fonts["small"], fill=ink)
    ds = f"Date: {fields['issue_date']}"
    draw.text((W - 85 - _tw(draw, ds, fonts["small"]), fy + 16), ds, font=fonts["small"], fill=ink)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 36 — Wide-margin formal with decorative rule
# ══════════════════════════════════════════════════════════════════════════════
def t36_wide_margin_formal(fields: dict) -> Image.Image:
    """Wide left margin with vertical decorative rule, clean body. Resembles
    letter-style degree certificates used by some UK and Commonwealth universities."""
    base  = (252, 252, 250)
    ink   = _sample_ink((20, 20, 30))
    ACCENT = (70, 50, 110)   # purple-navy
    RULE  = (170, 145, 60)   # gold vertical rule

    img  = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Vertical decorative rule in left margin
    rule_x = 120
    draw.rectangle([rule_x - 4, 0, rule_x, H], fill=ACCENT)
    draw.rectangle([rule_x + 4, 0, rule_x + 6, H], fill=RULE)

    # Top bar
    draw.rectangle([0, 0, W, 8], fill=ACCENT)
    draw.rectangle([0, H - 8, W, H], fill=ACCENT)

    y = 32
    cinzel = fonts.get("cinzel") or fonts["title"]
    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - rule_x - 100):
        tw_val = _tw(draw, ln, cinzel)
        x = rule_x + 40
        draw.text((x, y), ln, font=cinzel, fill=ACCENT)
        y += _th(draw, ln, cinzel) + 5
    y += 8
    disp = fonts.get("display") or fonts["heading"]
    # Title left-aligned in content zone
    draw.text((rule_x + 40, y), "DEGREE CERTIFICATE", font=disp, fill=RULE)
    y += 46

    draw.line([(rule_x + 30, y), (W - 50, y)], fill=ACCENT, width=1)
    y += 18

    # Prose body left-aligned in content zone
    prose = get_random_prose(fields)
    body_f  = fonts.get("antique")    or fonts["body"]
    proc_f  = fonts.get("antique_it") or fonts["body_italic"]
    script  = fonts.get("script")     or fonts["geo_title"]
    award_f = fonts.get("display")    or fonts["heading"]

    content_x = rule_x + 40
    max_w = W - content_x - 50

    if prose.proclamation:
        for ln in wrap_text(draw, prose.proclamation, proc_f, max_w):
            draw.text((content_x, y), ln, font=proc_f, fill=ink)
            y += _th(draw, ln, proc_f) + 5
        y += 10

    if prose.recipient_label:
        draw.text((content_x, y), prose.recipient_label.upper(), font=fonts["label"], fill=ink)
        y += 30

    for para in prose.body_paragraphs:
        p_clean = para.strip()
        if p_clean == fields["student_name"].strip():
            y += 8
            draw.text((content_x, y), p_clean, font=script, fill=ACCENT)
            y += _th(draw, p_clean, script) + 20
            continue
        for ln in para.split("\n"):
            ln = ln.strip()
            if not ln:
                y += 8
                continue
            for part in wrap_text(draw, ln, body_f, max_w):
                draw.text((content_x, y), part, font=body_f, fill=ink)
                y += _th(draw, part, body_f) + 5
        y += 10

    if prose.award_line:
        draw.line([(content_x, y), (W - 50, y)], fill=ACCENT, width=1)
        y += 12
        draw.text((content_x, y), prose.award_line.upper(), font=award_f, fill=ACCENT)
        y += 38

    if prose.closing_lines:
        draw.line([(content_x, y), (W - 50, y)], fill=ACCENT, width=1)
        y += 12
        for cl in prose.closing_lines:
            for ln in wrap_text(draw, cl, fonts["small"], max_w):
                draw.text((content_x, y), ln, font=fonts["small"], fill=ink)
                y += _th(draw, ln, fonts["small"]) + 4

    fy = H - 120
    draw.text((content_x, fy), fields["authority_name"], font=fonts["small"], fill=ink)
    draw.text((content_x, fy + 24), f"Date: {fields['issue_date']}", font=fonts["small"], fill=ink)
    return img


# ── Template list exported by this module ─────────────────────────────────────
TEMPLATES_V3 = [
    t29_fully_cursive_parchment,
    t30_name_at_top_banner,
    t31_label_value_grid,
    t32_gothic_blackletter,
    t33_sepia_worn_document,
    t34_double_border_vintage,
    t35_watermark_seal,
    t36_wide_margin_formal,
]

__all__ = ["TEMPLATES_V3", "BG_POOL"]
