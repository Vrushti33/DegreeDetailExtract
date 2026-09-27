"""Ten new certificate templates (t37–t46) — v4 complexity upgrade.

Each template addresses visual simplicity gaps identified from 60 real certificates:
  t37  Affiliated college header   — College + "Affiliated to [University]" pattern
  t38  Letterhead with address     — Full address header like real printed certs
  t39  Decorative seal circle      — Prominent circular emblem behind/beside text
  t40  Multi-authority block       — 3 signature slots at bottom (VC / Registrar / CoE)
  t41  Bilingual header deco       — Decorative non-Latin top line (regional language feel)
  t42  Compact info box            — All fields in a ruled table/box (transcript style)
  t43  Dark header band            — Navy/burgundy header band with white text
  t44  Two-column layout           — Fields in two columns, prose in center
  t45  Convocation style           — Date/venue/ceremony context added
  t46  Scroll / ribbon style       — Decorative ribbon banner for name + degree

All templates:
  - Use real paper backgrounds via realistic_bg when available
  - Render full prose through prose.get_random_prose()
  - Handle pass_class and student_name being empty
  - Vary layouts so Donut can't memorise field positions
"""

from __future__ import annotations

import random
import math
from typing import List

from PIL import Image, ImageDraw, ImageFilter

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
from .templates_v3 import _sample_bg, _sample_ink, _render_prose_body_v3, BG_POOL

# module-level pool — extended by renderer
BG_POOL_V4: List = BG_POOL  # share same pool as v3


# ── Shared helpers ────────────────────────────────────────────────────────────

def _draw_circle_seal(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int,
                       color, text: str = "", font=None, alpha: int = 30):
    """Draw a faint decorative seal ring at (cx, cy) with radius r."""
    # Outer ring
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=3)
    draw.ellipse([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8], outline=color, width=1)
    # Inner decorative cross/star
    draw.line([cx - r + 20, cy, cx + r - 20, cy], fill=color, width=1)
    draw.line([cx, cy - r + 20, cx, cy + r - 20], fill=color, width=1)
    # Ring text (abbreviated institution name around top arc)
    if text and font:
        # Place text segments around the top of the circle
        words = text.upper().split()[:4]
        short = "  ·  ".join(words)
        tw = _tw(draw, short, font)
        draw.text((cx - tw // 2, cy - r + 12), short, font=font, fill=color)


def _draw_authority_block(draw, fonts, fields, y_start, ink, margin=80):
    """Draw a 3-column authority/signature block at the bottom."""
    col_w = (W - margin * 2) // 3
    x_positions = [margin, margin + col_w, margin + col_w * 2]
    titles = [
        random.choice(["Registrar", "Deputy Registrar", "Academic Registrar"]),
        fields.get("authority_name", "") or random.choice(["Vice-Chancellor", "Principal", "Director"]),
        random.choice(["Controller of Examinations", "Dean of Studies", "Examination Officer"]),
    ]
    y = y_start
    hline(draw, y, ink, width=1, margin=margin)
    y += 14
    sf = fonts.get("small") or fonts["body"]
    for i, (x, title) in enumerate(zip(x_positions, titles)):
        # Signature line
        draw.line([(x + 10, y + 20), (x + col_w - 20, y + 20)], fill=ink, width=1)
        # Title below line
        for ln in wrap_text(draw, title, sf, col_w - 20):
            draw.text((x + 10, y + 26), ln, font=sf, fill=ink)
            y_tmp = y + 26 + _th(draw, ln, sf) + 4
    return y + 80


def _fake_address() -> str:
    """Generate a fake Indian-style institutional address."""
    areas = ["University Road", "Education Campus", "Knowledge Park",
             "Academic Avenue", "Gandhi Nagar", "Civil Lines",
             "Vidyanagar", "University Campus"]
    cities = ["Bangalore", "Mumbai", "Delhi", "Hyderabad", "Chennai",
              "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow"]
    states = ["Karnataka", "Maharashtra", "Tamil Nadu", "Telangana",
              "Gujarat", "Rajasthan", "West Bengal", "Uttar Pradesh"]
    pincodes = [f"{random.randint(1, 9)}{random.randint(10000, 99999)}" for _ in range(1)]
    city = random.choice(cities)
    state = random.choice(states)
    area = random.choice(areas)
    pin = random.randint(100000, 999999)
    return f"{area}, {city} – {pin}, {state}"


# Decorative Devanagari-style characters (Unicode) that render with Noto fonts
_DECO_LINES = [
    "॥ श्री ॥",
    "✦ ✦ ✦",
    "❖ ❖ ❖",
    "~ ~ ~",
    "· · · · ·",
]
_DECO_UNIV_SUFFIX = ["विश्वविद्यालय", "महाविद्यालय", "संस्थान", ""]


# ══════════════════════════════════════════════════════════════════════════════
#  Template 37 — Affiliated College Header
# ══════════════════════════════════════════════════════════════════════════════
def t37_affiliated_college(fields: dict) -> Image.Image:
    """College header with 'Affiliated to [Parent University]' sub-line.

    university_name field = the COLLEGE name (as annotated in real certs).
    The parent university shown in the sub-line is randomly generated and is
    NOT stored in the fields — the model must learn to ignore it.
    """
    base = random.choice([CREAM, OLD_LACE, IVORY, (248, 248, 255)])
    ink = _sample_ink((20, 30, 60))
    ACCENT = random.choice([NAVY, DARK_NAVY, BURGUNDY, DARK_GREEN])

    img = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()
    cinzel = fonts.get("cinzel") or fonts["title"]
    body = fonts.get("body") or fonts["body"]
    small = fonts.get("small") or fonts["small"]

    # Generate a fake parent university (NOT annotated)
    parent_univ_options = [
        f"University of {_fake_address().split(',')[1].strip()}",
        f"{random.choice(['Rajiv Gandhi', 'Anna', 'Osmania', 'Mumbai', 'Pune', 'Calcutta', 'Madras'])} University",
        f"Dr. {['APJ Abdul Kalam', 'B.R. Ambedkar', 'M.G.R.'][random.randint(0,2)]} Technological University",
    ]
    parent_univ = random.choice(parent_univ_options)

    y = 35
    # Top border
    draw.rectangle([20, 20, W - 20, H - 20], outline=ACCENT, width=3)
    draw.rectangle([28, 28, W - 28, H - 28], outline=ACCENT, width=1)

    # College name (= university_name field)
    college = fields["university_name"].upper()
    for ln in wrap_text(draw, college, cinzel, W - 120):
        h = draw_centered(draw, ln, y, cinzel, ACCENT)
        y += h + 6
    y += 4

    # "Affiliated to" sub-line (decorative — not annotated)
    aff_text = f"(Affiliated to {parent_univ})"
    y = draw_centered_wrapped(draw, aff_text, y, small, ink, W - 160, spacing=3)
    y += 4

    # Address line
    addr = _fake_address()
    y = draw_centered_wrapped(draw, addr, y, small, CHARCOAL, W - 160, spacing=2)
    y += 6

    hline(draw, y, ACCENT, width=2, margin=40)
    y += 8

    # "CERTIFICATE OF DEGREE" / "PROVISIONAL DEGREE CERTIFICATE"
    cert_titles = [
        "DEGREE CERTIFICATE",
        "PROVISIONAL DEGREE CERTIFICATE",
        "CERTIFICATE OF DEGREE CONFERMENT",
    ]
    disp = fonts.get("display") or fonts["heading"]
    draw_centered(draw, random.choice(cert_titles), y, disp, ACCENT)
    y += 48

    hline(draw, y, ACCENT, width=1, margin=60)
    y += 18

    prose = get_random_prose(fields)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=70)

    # Authority block at bottom
    _draw_authority_block(draw, fonts, fields, H - 140, ink, margin=70)
    draw.text((W - 220, H - 60), f"Date: {fields['issue_date']}", font=small, fill=ink)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 38 — Letterhead with Full Address
# ══════════════════════════════════════════════════════════════════════════════
def t38_letterhead_address(fields: dict) -> Image.Image:
    """Full institutional letterhead: university logo area, name, address, phone."""
    base = WHITE
    ink = (20, 20, 30)
    ACCENT = random.choice([NAVY, DARK_NAVY, DARK_GREEN, DARK_BLUE])

    img = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()
    cinzel = fonts.get("cinzel") or fonts["title"]
    small = fonts.get("small") or fonts["small"]
    body = fonts.get("body") or fonts["body"]

    # Top header band
    draw.rectangle([0, 0, W, 200], fill=ACCENT)

    # Placeholder logo circle (left side of header)
    draw.ellipse([40, 25, 150, 175], outline=GOLD, width=3, fill=None)
    draw.ellipse([55, 40, 135, 160], outline=GOLD, width=1)
    draw.text((70, 90), "SEAL", font=small, fill=GOLD)

    # University name in header
    univ = fields["university_name"].upper()
    y = 35
    for ln in wrap_text(draw, univ, cinzel, W - 220):
        h = draw_centered(draw, ln, y, cinzel, TEXT_WHITE)
        y += h + 5

    # Address line in header
    addr = _fake_address()
    draw_centered(draw, addr, y, small, (200, 200, 220))
    y += 26

    # Contact line
    phone = f"Ph: 0{random.randint(100,999)}-{random.randint(1000000,9999999)}  |  www.{fields['university_name'].split()[0].lower()}.edu.in"
    draw_centered(draw, phone, y + 4, small, (180, 180, 200))

    y = 220
    # NAAC / approval line
    naac_options = ["NAAC Accredited 'A' Grade", "UGC Recognized", "AICTE Approved", ""]
    naac = random.choice(naac_options)
    if naac:
        draw_centered(draw, naac, y, small, DARK_GOLD)
        y += 26

    hline(draw, y, ACCENT, width=2, margin=40)
    y += 12

    # Certificate title
    disp = fonts.get("display") or fonts["heading"]
    draw_centered(draw, "DEGREE CERTIFICATE", y, disp, ACCENT)
    y += 50
    hline(draw, y, ACCENT, width=1, margin=80)
    y += 18

    prose = get_random_prose(fields)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=70)

    # Footer
    fy = H - 130
    _draw_authority_block(draw, fonts, fields, fy, ink, margin=70)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 39 — Prominent Circular Seal
# ══════════════════════════════════════════════════════════════════════════════
def t39_seal_prominent(fields: dict) -> Image.Image:
    """Large decorative circular seal ring centered behind/beside the text body."""
    base = random.choice([CREAM, PARCHMENT, OLD_LACE])
    ink = _sample_ink((30, 25, 10))
    SEAL_COLOR = random.choice([GOLD, DARK_GOLD, NAVY, BURGUNDY])

    img = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()
    small = fonts.get("small") or fonts["small"]
    cinzel = fonts.get("cinzel") or fonts["title"]

    # Draw large faint seal in background (center of page)
    seal_r = random.randint(180, 240)
    seal_cx, seal_cy = W // 2, H // 2 + 50
    # Draw concentric rings (faint)
    for r_off, w in [(0, 3), (14, 1), (18, 1)]:
        draw.ellipse(
            [seal_cx - seal_r + r_off, seal_cy - seal_r + r_off,
             seal_cx + seal_r - r_off, seal_cy + seal_r - r_off],
            outline=(*SEAL_COLOR[:3], 60) if len(SEAL_COLOR) == 4 else SEAL_COLOR,
            width=w
        )
    # Inner cross
    draw.line([seal_cx - seal_r + 30, seal_cy, seal_cx + seal_r - 30, seal_cy],
              fill=SEAL_COLOR, width=1)
    draw.line([seal_cx, seal_cy - seal_r + 30, seal_cx, seal_cy + seal_r - 30],
              fill=SEAL_COLOR, width=1)

    # Certificate header
    y = 30
    draw.rectangle([20, 20, W - 20, H - 20], outline=SEAL_COLOR, width=2)

    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 120):
        y += draw_centered(draw, ln, y, cinzel, SEAL_COLOR) + 5
    hline(draw, y + 4, SEAL_COLOR, width=2, margin=60)
    y += 20

    disp = fonts.get("display") or fonts["heading"]
    draw_centered(draw, "CONVOCATION CERTIFICATE", y, disp, ink)
    y += 48

    prose = get_random_prose(fields)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=70)

    # Signature
    fy = H - 120
    hline(draw, fy, SEAL_COLOR, width=1, margin=70)
    auth = fields.get("authority_name", "")
    draw.text((90, fy + 16), auth, font=small, fill=ink)
    draw.text((90, fy + 38), f"Date: {fields['issue_date']}", font=small, fill=ink)
    # Place a small seal stamp bottom-right
    _draw_circle_seal(draw, W - 120, fy + 40, 60, SEAL_COLOR,
                      text=fields["university_name"], font=small)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 40 — Multi-Authority Signature Block
# ══════════════════════════════════════════════════════════════════════════════
def t40_multi_authority(fields: dict) -> Image.Image:
    """Three signature blocks at bottom — registrar / authority / CoE.
    authority_name fills only one slot; model must learn to pick the right one."""
    base = random.choice([WHITE, IVORY, (250, 250, 248)])
    ink = (15, 15, 25)
    ACCENT = random.choice([NAVY, BURGUNDY, DARK_GREEN])

    img = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()
    cinzel = fonts.get("cinzel") or fonts["title"]
    small = fonts.get("small") or fonts["small"]

    # Thin top + side rule
    draw.rectangle([18, 18, W - 18, H - 18], outline=ACCENT, width=2)

    y = 40
    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 100):
        y += draw_centered(draw, ln, y, cinzel, ACCENT) + 5
    hline(draw, y, ACCENT, width=2, margin=50)
    y += 14

    disp = fonts.get("display") or fonts["heading"]
    draw_centered(draw, "DEGREE CERTIFICATE", y, disp, ACCENT)
    y += 50
    hline(draw, y, ACCENT, width=1, margin=80)
    y += 16

    prose = get_random_prose(fields)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=70)

    # Multi-authority block
    _draw_authority_block(draw, fonts, fields, H - 150, ink, margin=60)
    draw_centered(draw, f"Date of Issue: {fields['issue_date']}", H - 30, small, ink)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 41 — Bilingual / Decorative Top Line
# ══════════════════════════════════════════════════════════════════════════════
def t41_bilingual_header(fields: dict) -> Image.Image:
    """Adds a decorative regional-language-style top line above English content.
    The top line is decorative only (not annotated) — model must ignore it."""
    base = random.choice([CREAM, OLD_LACE, (252, 250, 240)])
    ink = _sample_ink((30, 20, 10))
    ACCENT = random.choice([DARK_NAVY, BURGUNDY, DARK_GREEN, (100, 60, 20)])

    img = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()
    cinzel = fonts.get("cinzel") or fonts["title"]
    small = fonts.get("small") or fonts["small"]
    script = fonts.get("script") or fonts.get("geo_title") or fonts["title"]

    y = 30
    # Decorative top marker (regional language feel)
    deco = random.choice(_DECO_LINES)
    draw_centered(draw, deco, y, small, ACCENT)
    y += 30

    # University name in script font (stylised)
    for ln in wrap_text(draw, fields["university_name"], script, W - 100):
        y += draw_centered(draw, ln, y, script, ACCENT) + 6

    # Optional Devanagari suffix (decorative)
    suffix = random.choice(_DECO_UNIV_SUFFIX)
    if suffix:
        try:
            draw_centered(draw, suffix, y, small, ACCENT)
            y += 28
        except Exception:
            pass

    hline(draw, y, ACCENT, width=2, margin=50)
    y += 10

    draw_centered(draw, fields["university_name"].upper(), y, cinzel, ACCENT)
    y += 42
    hline(draw, y, ACCENT, width=1, margin=80)
    y += 14

    disp = fonts.get("display") or fonts["heading"]
    draw_centered(draw, "CERTIFICATE OF GRADUATION", y, disp, ink)
    y += 48

    prose = get_random_prose(fields)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=70)

    fy = H - 120
    hline(draw, fy, ACCENT, width=1, margin=70)
    draw.text((90, fy + 16), fields.get("authority_name", ""), font=small, fill=ink)
    draw.text((90, fy + 38), f"Date: {fields['issue_date']}", font=small, fill=ink)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 42 — Compact Info Table (Transcript Style)
# ══════════════════════════════════════════════════════════════════════════════
def t42_compact_info_table(fields: dict) -> Image.Image:
    """Fields presented in a ruled table/box — looks like a formal extract sheet."""
    base = WHITE
    ink = (10, 10, 10)
    ACCENT = random.choice([NAVY, DARK_NAVY, (0, 80, 60)])

    img = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()
    cinzel = fonts.get("cinzel") or fonts["title"]
    body = fonts.get("body") or fonts["body"]
    small = fonts.get("small") or fonts["small"]

    # Header band
    draw.rectangle([0, 0, W, 160], fill=ACCENT)
    y = 20
    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 80):
        y += draw_centered(draw, ln, y, cinzel, TEXT_WHITE) + 4
    draw_centered(draw, _fake_address(), y + 6, small, (200, 210, 220))

    y = 175
    disp = fonts.get("display") or fonts["heading"]
    draw_centered(draw, "DEGREE CERTIFICATE", y, disp, ACCENT)
    y += 50

    # Short prose opening
    prose = get_random_prose(fields)
    if prose.proclamation:
        y = draw_centered_wrapped(draw, prose.proclamation, y,
                                   fonts.get("body_italic") or body, ink, W - 140, spacing=4)
        y += 14

    # Ruled table of field:value
    TABLE_X = 80
    TABLE_W = W - 160
    COL_LABEL = 280
    ROW_H = 36

    field_rows = [
        ("Name of Student",     fields.get("student_name", "")),
        ("University / Institution", fields.get("university_name", "")),
        ("Degree / Programme",  fields.get("course_name", "")),
        ("Specialization",      fields.get("specialization", "") or "—"),
        ("Class / Grade",       fields.get("pass_class", "") or "—"),
        ("Authority",           fields.get("authority_name", "") or "—"),
        ("Date of Award",       fields.get("issue_date", "")),
    ]

    # Table outline
    table_h = ROW_H * len(field_rows) + 2
    draw.rectangle([TABLE_X, y, TABLE_X + TABLE_W, y + table_h], outline=ACCENT, width=2)
    draw.line([TABLE_X + COL_LABEL, y, TABLE_X + COL_LABEL, y + table_h], fill=ACCENT, width=1)

    for i, (label, value) in enumerate(field_rows):
        row_y = y + i * ROW_H
        # Alternating row shading
        if i % 2 == 0:
            draw.rectangle([TABLE_X + 1, row_y + 1, TABLE_X + TABLE_W - 1, row_y + ROW_H - 1],
                           fill=(245, 247, 250))
        draw.line([TABLE_X, row_y + ROW_H, TABLE_X + TABLE_W, row_y + ROW_H], fill=ACCENT, width=1)
        draw.text((TABLE_X + 8, row_y + 8), label, font=small, fill=ACCENT)
        # Value (may be long — wrap)
        val_lines = wrap_text(draw, str(value), small, TABLE_W - COL_LABEL - 16)
        for j, vl in enumerate(val_lines[:2]):
            draw.text((TABLE_X + COL_LABEL + 8, row_y + 8 + j * 16), vl, font=small, fill=ink)

    y += table_h + 30

    # Seal and signature
    _draw_circle_seal(draw, W - 140, y + 60, 70, ACCENT,
                      text=fields["university_name"], font=small)

    draw.text((TABLE_X, y + 20), "Certified that the above information is correct.", font=small, fill=ink)
    draw.text((TABLE_X, y + 42), f"Place: {random.choice(['Bangalore', 'Mumbai', 'Delhi', 'Chennai'])}", font=small, fill=ink)
    draw.text((TABLE_X, y + 62), f"Date:  {fields['issue_date']}", font=small, fill=ink)

    fy = H - 90
    hline(draw, fy, ACCENT, width=1, margin=TABLE_X)
    draw.text((TABLE_X, fy + 14), fields.get("authority_name", ""), font=small, fill=ink)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 43 — Dark Header Band
# ══════════════════════════════════════════════════════════════════════════════
def t43_dark_header_band(fields: dict) -> Image.Image:
    """Navy/Burgundy full-width header band with white text. Common in modern certs."""
    BAND_COLOR = random.choice([NAVY, DARK_NAVY, BURGUNDY, (40, 60, 40), DARK_BLUE])
    base = random.choice([WHITE, IVORY, (252, 252, 255)])
    ink = (15, 15, 25)

    img = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()
    cinzel = fonts.get("cinzel") or fonts["title"]
    small = fonts.get("small") or fonts["small"]

    # Full-width top band
    BAND_H = random.randint(170, 220)
    draw.rectangle([0, 0, W, BAND_H], fill=BAND_COLOR)

    # Gold accent line at band bottom
    draw.rectangle([0, BAND_H - 6, W, BAND_H], fill=GOLD)

    y = 25
    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 60):
        y += draw_centered(draw, ln, y, cinzel, TEXT_WHITE) + 6
    addr = _fake_address()
    draw_centered(draw, addr, y, small, (200, 210, 220))
    y += 24
    naac = random.choice(["NAAC 'A++' Accredited", "ISO 9001:2015 Certified", ""])
    if naac:
        draw_centered(draw, naac, y, small, GOLD)

    y = BAND_H + 22
    disp = fonts.get("display") or fonts["heading"]
    draw_centered(draw, "CERTIFICATE OF DEGREE", y, disp, BAND_COLOR)
    y += 50
    hline(draw, y, BAND_COLOR, width=1, margin=80)
    y += 18

    prose = get_random_prose(fields)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=70)

    # Bottom band (thin)
    draw.rectangle([0, H - 50, W, H], fill=BAND_COLOR)
    draw.text((80, H - 36), fields.get("authority_name", ""), font=small, fill=TEXT_WHITE)
    draw.text((W - 280, H - 36), f"Date: {fields['issue_date']}", font=small, fill=TEXT_WHITE)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 44 — Two-Column Info Layout
# ══════════════════════════════════════════════════════════════════════════════
def t44_two_column_info(fields: dict) -> Image.Image:
    """Left column: logo+seal area. Right column: fields and authority info."""
    base = random.choice([CREAM, WHITE, OLD_LACE])
    ink = (20, 20, 30)
    ACCENT = random.choice([NAVY, DARK_NAVY, BURGUNDY])

    img = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()
    cinzel = fonts.get("cinzel") or fonts["title"]
    small = fonts.get("small") or fonts["small"]
    body = fonts.get("body") or fonts["body"]

    # Full border
    draw.rectangle([15, 15, W - 15, H - 15], outline=ACCENT, width=3)
    draw.rectangle([25, 25, W - 25, H - 25], outline=GOLD, width=1)

    # Header spanning full width
    y = 40
    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 80):
        y += draw_centered(draw, ln, y, cinzel, ACCENT) + 5
    hline(draw, y, ACCENT, width=2, margin=40)
    y += 12
    draw_centered(draw, "DEGREE CERTIFICATE", y, fonts.get("display") or fonts["heading"], ACCENT)
    y += 50
    hline(draw, y, ACCENT, width=1, margin=60)
    y += 20

    # Left column: seal
    COL1_W = 280
    seal_cx = 30 + COL1_W // 2
    seal_cy = y + 200
    _draw_circle_seal(draw, seal_cx, seal_cy, 110, ACCENT,
                      text=fields["university_name"], font=small)

    # Right column: fields
    rx = 30 + COL1_W + 30
    rw = W - rx - 40
    ry = y + 10

    field_rows = [
        ("Student Name",   fields.get("student_name", "")),
        ("Degree",         fields.get("course_name", "")),
        ("Specialization", fields.get("specialization", "") or "Not Applicable"),
        ("Class of Award", fields.get("pass_class", "") or "—"),
        ("Date of Issue",  fields.get("issue_date", "")),
    ]
    for label, value in field_rows:
        draw.text((rx, ry), label + ":", font=small, fill=ACCENT)
        ry += 20
        for vl in wrap_text(draw, value, body, rw):
            draw.text((rx + 10, ry), vl, font=body, fill=ink)
            ry += _th(draw, vl, body) + 3
        hline_partial = True
        draw.line([(rx, ry + 4), (rx + rw, ry + 4)], fill=(200, 200, 200), width=1)
        ry += 16

    # Authority
    ry += 10
    draw.text((rx, ry), "Authorised by:", font=small, fill=ACCENT)
    ry += 22
    draw.text((rx, ry), fields.get("authority_name", ""), font=body, fill=ink)

    fy = H - 60
    hline(draw, fy, ACCENT, width=1, margin=40)
    draw_centered(draw, f"Date: {fields['issue_date']}", fy + 16, small, ink)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 45 — Convocation Style (with ceremony context)
# ══════════════════════════════════════════════════════════════════════════════
def t45_convocation_style(fields: dict) -> Image.Image:
    """Adds convocation/ceremony context: year, venue, convocation number."""
    base = random.choice([PARCHMENT, CREAM, IVORY])
    ink = _sample_ink((25, 20, 10))
    ACCENT = random.choice([DARK_GOLD, GOLDEN_BROWN, BURGUNDY])

    img = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()
    cinzel = fonts.get("cinzel") or fonts["title"]
    small = fonts.get("small") or fonts["small"]
    script = fonts.get("script") or fonts.get("geo_title") or fonts["title"]

    # Decorative corners
    corner_size = 60
    for cx, cy in [(0, 0), (W - corner_size, 0), (0, H - corner_size), (W - corner_size, H - corner_size)]:
        draw.rectangle([cx + 8, cy + 8, cx + corner_size - 8, cy + corner_size - 8],
                       outline=ACCENT, width=2)

    draw.rectangle([30, 30, W - 30, H - 30], outline=ACCENT, width=2)

    y = 50
    # Convocation number + year (decorative context)
    issue_year = fields.get("issue_date", "2020")[-4:] if len(fields.get("issue_date", "")) >= 4 else "2020"
    conv_num = random.randint(10, 55)
    conv_line = f"{conv_num}th Convocation Ceremony  ·  {issue_year}"
    draw_centered(draw, conv_line, y, small, ACCENT)
    y += 28

    hline(draw, y, ACCENT, width=1, margin=50)
    y += 10

    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 100):
        y += draw_centered(draw, ln, y, cinzel, ACCENT) + 5
    hline(draw, y, ACCENT, width=2, margin=50)
    y += 14

    draw_centered(draw, "DEGREE CERTIFICATE", y, fonts.get("display") or fonts["heading"], ink)
    y += 46
    hline(draw, y, ACCENT, width=1, margin=80)
    y += 16

    prose = get_random_prose(fields)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=70)

    # Venue line
    venues = ["Main Auditorium", "University Grounds", "Convention Centre", "Open Air Theatre"]
    venue_line = f"Venue: {random.choice(venues)}, {issue_year}"
    y = max(y, H - 190)
    draw_centered(draw, venue_line, y, small, CHARCOAL)
    y += 22

    _draw_authority_block(draw, fonts, fields, H - 140, ink, margin=70)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 46 — Scroll / Ribbon Style
# ══════════════════════════════════════════════════════════════════════════════
def t46_scroll_ribbon(fields: dict) -> Image.Image:
    """Decorative ribbon banner across the page holding the student name + degree.
    Simulates the prominent name-on-scroll style common in South Asian certs."""
    base = random.choice([CREAM, IVORY, (250, 248, 240)])
    ink = _sample_ink((30, 20, 5))
    RIBBON = random.choice([NAVY, BURGUNDY, DARK_GREEN, (100, 60, 10)])

    img = _sample_bg(base_color=base)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()
    cinzel = fonts.get("cinzel") or fonts["title"]
    script = fonts.get("script") or fonts.get("geo_title") or fonts["title"]
    small = fonts.get("small") or fonts["small"]

    draw.rectangle([18, 18, W - 18, H - 18], outline=RIBBON, width=3)
    draw.rectangle([28, 28, W - 28, H - 28], outline=GOLD, width=1)

    y = 42
    for ln in wrap_text(draw, fields["university_name"].upper(), cinzel, W - 100):
        y += draw_centered(draw, ln, y, cinzel, RIBBON) + 5
    hline(draw, y, RIBBON, width=2, margin=50)
    y += 14

    draw_centered(draw, "CERTIFICATE OF DEGREE", y, fonts.get("display") or fonts["heading"], ink)
    y += 46

    # Ribbon banner for student name
    ribbon_top = y
    ribbon_bot = y + 80
    draw.rectangle([40, ribbon_top, W - 40, ribbon_bot], fill=RIBBON)
    # Ribbon end flaps (triangular notch effect)
    draw.polygon([(40, ribbon_top), (40, ribbon_bot), (20, (ribbon_top + ribbon_bot) // 2)], fill=RIBBON)
    draw.polygon([(W - 40, ribbon_top), (W - 40, ribbon_bot), (W - 20, (ribbon_top + ribbon_bot) // 2)], fill=RIBBON)

    # Student name on ribbon
    name = fields.get("student_name", "")
    if name:
        for ln in wrap_text(draw, name, script, W - 140):
            draw_centered(draw, ln, ribbon_top + 18, script, TEXT_WHITE)

    y = ribbon_bot + 22

    # Degree info line
    course = fields.get("course_name", "")
    spec = fields.get("specialization", "")
    degree_line = course + (f" — {spec}" if spec else "")
    y = draw_centered_wrapped(draw, degree_line, y, cinzel, RIBBON, W - 120, spacing=4)
    y += 16
    hline(draw, y, RIBBON, width=1, margin=80)
    y += 14

    prose = get_random_prose(fields)
    y = _render_prose_body_v3(draw, fonts, fields, prose, y, ink, margin=70)

    fy = H - 120
    _draw_authority_block(draw, fonts, fields, fy, ink, margin=70)
    return img


# ── Template list exported by this module ─────────────────────────────────────
TEMPLATES_V4 = [
    t37_affiliated_college,
    t38_letterhead_address,
    t39_seal_prominent,
    t40_multi_authority,
    t41_bilingual_header,
    t42_compact_info_table,
    t43_dark_header_band,
    t44_two_column_info,
    t45_convocation_style,
    t46_scroll_ribbon,
]

__all__ = ["TEMPLATES_V4", "BG_POOL_V4"]
