"""Pillow-only certificate template implementations.

Each template function has the signature:
    tXX_name(fields: dict) -> PIL.Image.Image

`fields` contains: student_name, university_name, course_name,
specialization, pass_class, authority_name, issue_date.

All templates produce 1000 × 1400 px RGB images.
Templates are collected in the TEMPLATES list at the bottom of the module.
"""

from PIL import Image, ImageDraw

from .fonts import get_fonts

# ── Canvas dimensions ─────────────────────────────────────────────────────────
W, H = 1000, 1400

# ── Color palette ─────────────────────────────────────────────────────────────
CREAM        = (253, 251, 240)
PARCHMENT    = (253, 245, 220)
OLD_LACE     = (253, 245, 230)
IVORY        = (255, 255, 240)
WHITE        = (255, 255, 255)
LIGHT_GREY   = (245, 245, 245)
LIGHT_BLUE   = (240, 248, 255)
LIGHT_GREEN  = (248, 251, 245)
LIGHT_YELLOW = (255, 253, 231)

NAVY         = (26, 58, 92)
DARK_NAVY    = (15, 38, 62)
BURGUNDY     = (107, 0, 32)
DARK_GREEN   = (27, 94, 32)
CHARCOAL     = (66, 66, 66)
DARK_BLUE    = (0, 51, 102)
SLATE        = (96, 125, 139)

BROWN        = (101, 67, 33)
GOLDEN_BROWN = (139, 105, 20)
GOLD         = (180, 140, 20)
BRIGHT_GOLD  = (212, 175, 55)
WARM_GOLD    = (196, 158, 40)
DARK_GOLD    = (184, 134, 11)

TEXT_BLACK   = (20, 20, 20)
TEXT_DARK    = (40, 20, 10)
TEXT_NAVY    = (15, 45, 75)
TEXT_GREEN   = (20, 70, 25)
TEXT_WHITE   = (255, 255, 255)
TEXT_CREAM   = (253, 245, 220)
TEXT_DARK_RED = (80, 0, 20)


# ══════════════════════════════════════════════════════════════════════════════
#  Drawing utilities
# ══════════════════════════════════════════════════════════════════════════════

def _tw(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _th(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]


def draw_centered(draw, text, y, font, color) -> int:
    """Draw *text* centred horizontally at *y*. Returns the line height."""
    x = (W - _tw(draw, text, font)) // 2
    draw.text((x, y), text, font=font, fill=color)
    return _th(draw, text, font)


def wrap_text(draw, text, font, max_width) -> list:
    """Word-wrap *text* to fit within *max_width* pixels."""
    words = text.split()
    if not words:
        return [""]
    lines, current = [], []
    for word in words:
        test = " ".join(current + [word])
        if _tw(draw, test, font) <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines or [""]


def draw_centered_wrapped(draw, text, y, font, color, max_width, spacing=8) -> int:
    """Draw word-wrapped text centred. Returns y after the last line."""
    for line in wrap_text(draw, text, font, max_width):
        h = draw_centered(draw, line, y, font, color)
        y += h + spacing
    return y


def hline(draw, y, color, width=1, margin=60):
    draw.line([(margin, y), (W - margin, y)], fill=color, width=width)


def double_hline(draw, y, color, gap=6, w1=2, w2=1, margin=60):
    draw.line([(margin, y),       (W - margin, y)],       fill=color, width=w1)
    draw.line([(margin, y + gap), (W - margin, y + gap)], fill=color, width=w2)


# ══════════════════════════════════════════════════════════════════════════════
#  Template 01 — Classic Parchment
# ══════════════════════════════════════════════════════════════════════════════
def t01_classic_parchment(fields: dict) -> Image.Image:
    """Warm cream/parchment, saddlebrown double border, centered formal prose."""
    BORDER  = (139, 69, 19)
    GOLD_LN = GOLD
    ACCENT  = (120, 60, 10)

    img  = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Outer + inner border
    draw.rectangle([18, 18, W - 18, H - 18], outline=BORDER, width=4)
    draw.rectangle([32, 32, W - 32, H - 32], outline=BORDER, width=1)
    # Corner squares
    for cx, cy in [(18, 18), (W - 18, 18), (18, H - 18), (W - 18, H - 18)]:
        draw.rectangle([cx - 10, cy - 10, cx + 10, cy + 10], fill=BORDER)

    y = 75
    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["title"], W - 160):
        y += draw_centered(draw, ln, y, fonts["title"], TEXT_DARK) + 6
    y += 16

    hline(draw, y, GOLD_LN, width=2, margin=80)
    y += 8
    hline(draw, y, BORDER, width=1, margin=80)
    y += 32

    draw_centered(draw, "THIS IS TO CERTIFY THAT", y, fonts["heading"], ACCENT)
    y += 58

    h = draw_centered(draw, fields["student_name"], y, fonts["geo_title"], TEXT_DARK)
    y += h + 12
    nw = _tw(draw, fields["student_name"], fonts["geo_title"])
    draw.line([(W//2 - nw//2, y), (W//2 + nw//2, y)], fill=GOLD_LN, width=2)
    y += 24

    y = draw_centered_wrapped(
        draw, "has successfully fulfilled all requirements for the degree of",
        y, fonts["body"], TEXT_DARK, W - 220, spacing=6,
    )
    y += 10

    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], TEXT_DARK) + 10
    y += draw_centered(draw, f"in  {fields['specialization']}", y, fonts["body_italic"], TEXT_DARK) + 24

    hline(draw, y, GOLD_LN, width=1, margin=160)
    y += 18
    y += draw_centered(draw, f"Awarded with:  {fields['pass_class']}", y, fonts["heading"], ACCENT) + 48

    # Signature block
    fy = H - 190
    hline(draw, fy, GOLD_LN, width=1, margin=80)
    hline(draw, fy + 5, BORDER, width=2, margin=80)
    draw.text((100, fy + 22), "Authorised by:", font=fonts["small"], fill=TEXT_DARK)
    draw.text((100, fy + 46), fields["authority_name"], font=fonts["body"], fill=TEXT_DARK)
    ds = f"Date of Issue:  {fields['issue_date']}"
    draw.text((W - 110 - _tw(draw, ds, fonts["body"]), fy + 46), ds, font=fonts["body"], fill=TEXT_DARK)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 02 — Modern Navy
# ══════════════════════════════════════════════════════════════════════════════
def t02_modern_navy(fields: dict) -> Image.Image:
    """Navy header/footer bands, white body, label-value table layout."""
    ACCENT = (52, 110, 170)

    img  = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    HH = 185
    draw.rectangle([0, 0, W, HH], fill=NAVY)
    draw.rectangle([0, H - 75, W, H], fill=NAVY)
    draw.line([(0, HH), (W, HH)], fill=BRIGHT_GOLD, width=3)
    draw.line([(0, H - 75), (W, H - 75)], fill=BRIGHT_GOLD, width=3)

    y = 28
    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["subtitle"], W - 100):
        y += draw_centered(draw, ln, y, fonts["subtitle"], TEXT_WHITE) + 6
    y += 6
    draw_centered(draw, "DEGREE CERTIFICATE", y, fonts["heading"], BRIGHT_GOLD)
    y = HH + 36

    draw_centered(draw, "This is to certify that", y, fonts["body_italic"], (100, 100, 100))
    y += 46

    h = draw_centered(draw, fields["student_name"], y, fonts["geo_title"], (20, 20, 80))
    y += h + 10
    nw = _tw(draw, fields["student_name"], fonts["geo_title"])
    draw.line([(W//2 - nw//2, y), (W//2 + nw//2, y)], fill=ACCENT, width=2)
    y += 30

    LX, VX = 120, 340
    for label, value in [
        ("Degree",         fields["course_name"]),
        ("Specialization", fields["specialization"]),
        ("Class Awarded",  fields["pass_class"]),
        ("Date of Issue",  fields["issue_date"]),
    ]:
        draw.text((LX, y), label + ":", font=fonts["label"], fill=SLATE)
        for ln in wrap_text(draw, value, fonts["value"], W - VX - 80):
            draw.text((VX, y), ln, font=fonts["value"], fill=TEXT_BLACK)
            y += _th(draw, ln, fonts["value"]) + 4
        y += 12

    y += 28
    hline(draw, y, (200, 200, 200), margin=100)
    y += 20
    draw.text((LX, y), "Signed by:", font=fonts["small"], fill=SLATE)
    y += 24
    for ln in wrap_text(draw, fields["authority_name"], fonts["body"], W - 200):
        draw.text((LX, y), ln, font=fonts["body"], fill=TEXT_BLACK)
        y += _th(draw, ln, fonts["body"]) + 4

    draw_centered(draw, "Excellence in Education", H - 50, fonts["small"], TEXT_WHITE)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 03 — Royal Burgundy
# ══════════════════════════════════════════════════════════════════════════════
def t03_royal_burgundy(fields: dict) -> Image.Image:
    """Ivory bg, thick burgundy outer + thin gold inner border, formal centered."""
    img  = Image.new("RGB", (W, H), IVORY)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([15, 15, W - 15, H - 15], outline=BURGUNDY, width=6)
    draw.rectangle([30, 30, W - 30, H - 30], outline=GOLDEN_BROWN, width=1)
    # Corner diamonds
    for cx, cy in [(15, 15), (W - 15, 15), (15, H - 15), (W - 15, H - 15)]:
        draw.polygon([(cx, cy - 12), (cx + 12, cy), (cx, cy + 12), (cx - 12, cy)], fill=BURGUNDY)

    y = 72
    draw_centered(draw, "UNIVERSITY DEGREE CERTIFICATE", y, fonts["heading"], GOLDEN_BROWN)
    y += 44
    double_hline(draw, y, BURGUNDY, gap=8, w1=3, w2=1, margin=60)
    y += 30

    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["title"], W - 140):
        y += draw_centered(draw, ln, y, fonts["title"], TEXT_DARK_RED) + 6
    y += 24

    double_hline(draw, y, BURGUNDY, gap=8, w1=3, w2=1, margin=60)
    y += 32

    draw_centered(draw, "Hereby confers upon", y, fonts["body_italic"], (110, 60, 50))
    y += 52

    h = draw_centered(draw, fields["student_name"], y, fonts["geo_title"], TEXT_DARK)
    y += h + 12
    nw = _tw(draw, fields["student_name"], fonts["geo_title"])
    draw.line([(W//2 - nw//2 - 20, y), (W//2 + nw//2 + 20, y)], fill=BRIGHT_GOLD, width=2)
    y += 28

    y = draw_centered_wrapped(draw, "the degree of", y, fonts["body_italic"], (110, 60, 50), W - 200)
    y += 6

    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], TEXT_DARK_RED) + 6
    y += draw_centered(draw, f"({fields['specialization']})", y, fonts["body_italic"], TEXT_DARK) + 22

    hline(draw, y, GOLDEN_BROWN, width=1, margin=150)
    y += 18
    y += draw_centered(draw, f"Class:  {fields['pass_class']}", y, fonts["heading"], TEXT_DARK_RED) + 50

    fy = H - 175
    double_hline(draw, fy, BURGUNDY, gap=7, w1=2, w2=1, margin=60)
    draw.text((80, fy + 24), "Signed:", font=fonts["small"], fill=TEXT_DARK)
    draw.text((80, fy + 46), fields["authority_name"], font=fonts["body"], fill=TEXT_DARK)
    draw.text((80, fy + 82), f"Date: {fields['issue_date']}", font=fonts["body"], fill=TEXT_DARK)
    # Seal circle
    cx, cy, r = W - 130, H - 115, 60
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=BURGUNDY, width=3)
    draw.ellipse([cx-r+8, cy-r+8, cx+r-8, cy+r-8], outline=GOLDEN_BROWN, width=1)
    draw_centered(draw, "SEAL", cy - 10, fonts["small"], BURGUNDY)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 04 — Emerald Formal
# ══════════════════════════════════════════════════════════════════════════════
def t04_emerald_formal(fields: dict) -> Image.Image:
    """Light green bg, dark-green border + gold accent lines, horizontal dividers."""
    img  = Image.new("RGB", (W, H), LIGHT_GREEN)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([18, 18, W - 18, H - 18], outline=DARK_GREEN, width=5)
    draw.rectangle([28, 28, W - 28, H - 28], outline=WARM_GOLD, width=1)

    y = 66
    y += draw_centered(draw, fields["university_name"].upper(), y, fonts["title"], DARK_GREEN) + 8
    double_hline(draw, y, WARM_GOLD, gap=6, w1=2, w2=1, margin=60)
    y += 32
    draw_centered(draw, "OFFICIAL DEGREE CERTIFICATE", y, fonts["heading"], WARM_GOLD)
    y += 52

    draw_centered(draw, "This certifies that", y, fonts["body_italic"], TEXT_GREEN)
    y += 46

    y += draw_centered(draw, fields["student_name"], y, fonts["geo_title"], TEXT_DARK) + 24

    hline(draw, y, DARK_GREEN, width=2, margin=80)
    y += 26

    y = draw_centered_wrapped(
        draw, "has completed all requirements and is hereby awarded the degree of",
        y, fonts["body"], TEXT_DARK, W - 200,
    )
    y += 12

    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], DARK_GREEN) + 8
    y += draw_centered(draw, f"Specialization: {fields['specialization']}", y, fonts["body"], TEXT_GREEN) + 28

    hline(draw, y, WARM_GOLD, width=1, margin=120)
    y += 18
    y += draw_centered(draw, f"Awarded with {fields['pass_class']}", y, fonts["heading"], DARK_GREEN) + 58

    fy = H - 162
    draw.line([(60, fy), (W - 60, fy)], fill=WARM_GOLD, width=2)
    draw.text((80, fy + 20), "Authorising Officer:", font=fonts["small"], fill=TEXT_GREEN)
    draw.text((80, fy + 42), fields["authority_name"], font=fonts["body"], fill=TEXT_DARK)
    ds = f"Issued: {fields['issue_date']}"
    draw.text((W - 90 - _tw(draw, ds, fonts["body"]), fy + 42), ds, font=fonts["body"], fill=TEXT_DARK)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 05 — Minimalist Slate
# ══════════════════════════════════════════════════════════════════════════════
def t05_minimalist_slate(fields: dict) -> Image.Image:
    """White bg, thin blue-grey border, left-accent bar, label-value layout."""
    BORDER = (176, 196, 205)
    LABEL  = (120, 120, 130)

    img  = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([25, 25, W - 25, H - 25], outline=BORDER, width=1)
    draw.rectangle([25, 25, 32, H - 25], fill=SLATE)   # left accent bar

    y = 65
    for ln in wrap_text(draw, fields["university_name"], fonts["subtitle"], W - 160):
        draw.text((65, y), ln, font=fonts["subtitle"], fill=SLATE)
        y += _th(draw, ln, fonts["subtitle"]) + 6
    y += 10
    draw.line([(65, y), (W - 60, y)], fill=BORDER)
    y += 26

    draw.text((65, y), "DEGREE CERTIFICATE", font=fonts["heading"], fill=(80, 80, 90))
    y += 52

    draw.text((65, y), "Awarded to", font=fonts["small"], fill=LABEL)
    y += 24
    draw.text((65, y), fields["student_name"], font=fonts["geo_title"], fill=(20, 20, 60))
    y += _th(draw, fields["student_name"], fonts["geo_title"]) + 32

    LX, VX = 65, 300
    for lbl, val in [
        ("Degree",         fields["course_name"]),
        ("Specialization", fields["specialization"]),
        ("Class",          fields["pass_class"]),
        ("University",     fields["university_name"]),
        ("Date Issued",    fields["issue_date"]),
        ("Authorised by",  fields["authority_name"]),
    ]:
        draw.text((LX, y), lbl, font=fonts["label"], fill=LABEL)
        draw.line([(LX, y + 27), (VX - 15, y + 27)], fill=BORDER)
        for ln in wrap_text(draw, val, fonts["value"], W - VX - 60):
            draw.text((VX, y), ln, font=fonts["value"], fill=TEXT_BLACK)
            y += _th(draw, ln, fonts["value"]) + 4
        y += 16

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 06 — Gold Ornate
# ══════════════════════════════════════════════════════════════════════════════
def t06_gold_ornate(fields: dict) -> Image.Image:
    """Light yellow bg, triple gold border, circular seal, formal centered."""
    G1   = BRIGHT_GOLD
    G2   = (160, 120, 10)
    G3   = WARM_GOLD
    DARK = (50, 35, 0)

    img  = Image.new("RGB", (W, H), LIGHT_YELLOW)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([12, 12, W - 12, H - 12], outline=G1, width=4)
    draw.rectangle([22, 22, W - 22, H - 22], outline=G2, width=1)
    draw.rectangle([28, 28, W - 28, H - 28], outline=G3, width=1)
    for cx, cy in [(12, 12), (W - 12, 12), (12, H - 12), (W - 12, H - 12)]:
        draw.polygon([(cx, cy - 14), (cx + 14, cy), (cx, cy + 14), (cx - 14, cy)], fill=G1)

    y = 75
    draw_centered(draw, "CERTIFICATE OF DEGREE", y, fonts["heading"], G2)
    y += 50
    hline(draw, y, G1, width=2, margin=60)
    y += 20

    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["title"], W - 140):
        y += draw_centered(draw, ln, y, fonts["title"], DARK) + 6
    y += 16

    hline(draw, y, G1, width=2, margin=60)
    y += 32

    draw_centered(draw, "This is to certify that", y, fonts["body_italic"], (100, 80, 0))
    y += 52

    h = draw_centered(draw, fields["student_name"], y, fonts["geo_title"], TEXT_DARK)
    y += h + 18

    y = draw_centered_wrapped(draw, "has been awarded the degree of", y, fonts["body"], (80, 60, 0), W - 200)
    y += 10

    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], DARK) + 8
    y += draw_centered(draw, f"in  {fields['specialization']}", y, fonts["body_italic"], TEXT_DARK) + 22

    hline(draw, y, G2, width=1, margin=150)
    y += 18
    y += draw_centered(draw, f"Class of Award:  {fields['pass_class']}", y, fonts["heading"], DARK) + 38

    # Circular seal
    cx, cy, r = W // 2, y + 65, 58
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=G1, width=3)
    draw.ellipse([cx-r+9, cy-r+9, cx+r-9, cy+r-9], outline=G2, width=1)
    draw_centered(draw, "SEAL", cy - 10, fonts["small"], G2)
    y = cy + r + 30

    draw.text((80, y), fields["authority_name"], font=fonts["body"], fill=TEXT_DARK)
    ds = fields["issue_date"]
    draw.text((W - 90 - _tw(draw, ds, fonts["body"]), y), ds, font=fonts["body"], fill=TEXT_DARK)
    draw.line([(80, y + 30), (350, y + 30)], fill=G2, width=1)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 07 — Charcoal Silver
# ══════════════════════════════════════════════════════════════════════════════
def t07_charcoal_silver(fields: dict) -> Image.Image:
    """Light grey bg, double charcoal border, sophisticated centered layout."""
    SILVER = (150, 150, 160)
    BORDER2 = (160, 160, 160)
    ACCENT  = (80, 80, 90)

    img  = Image.new("RGB", (W, H), (248, 248, 248))
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([16, 16, W - 16, H - 16], outline=CHARCOAL, width=4)
    draw.rectangle([26, 26, W - 26, H - 26], outline=BORDER2, width=1)

    y = 72
    draw_centered(draw, "— OFFICIAL DEGREE CERTIFICATE —", y, fonts["heading"], SILVER)
    y += 52
    hline(draw, y, CHARCOAL, width=2, margin=50)
    y += 20

    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["title"], W - 120):
        y += draw_centered(draw, ln, y, fonts["title"], CHARCOAL) + 6
    y += 22

    hline(draw, y, BORDER2, width=1, margin=100)
    y += 30

    draw_centered(draw, "This certificate is awarded to", y, fonts["body_italic"], ACCENT)
    y += 52

    y += draw_centered(draw, fields["student_name"], y, fonts["geo_title"], CHARCOAL) + 22

    draw_centered(draw, "for the successful completion of", y, fonts["body_italic"], ACCENT)
    y += 46

    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], TEXT_BLACK) + 8
    y += draw_centered(draw, f"({fields['specialization']})", y, fonts["body"], ACCENT) + 28

    hline(draw, y, BORDER2, width=1, margin=150)
    y += 22
    y += draw_centered(draw, f"Result:  {fields['pass_class']}", y, fonts["heading"], CHARCOAL) + 50

    hline(draw, H - 170, CHARCOAL, width=2, margin=50)
    draw.text((70, H - 152), fields["authority_name"], font=fonts["body"], fill=TEXT_BLACK)
    draw.text((70, H - 116), f"Date: {fields['issue_date']}", font=fonts["small"], fill=ACCENT)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 08 — Government Official
# ══════════════════════════════════════════════════════════════════════════════
def t08_government_official(fields: dict) -> Image.Image:
    """White bg, triple-parallel border, very formal government-style centered."""
    B2    = (80, 80, 80)
    B3    = (150, 150, 150)
    ACNT  = (50, 50, 80)

    img  = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([10, 10, W - 10, H - 10], outline=(30, 30, 30), width=4)
    draw.rectangle([20, 20, W - 20, H - 20], outline=B2, width=2)
    draw.rectangle([30, 30, W - 30, H - 30], outline=B3, width=1)

    y = 68
    draw_centered(draw, "GOVERNMENT OF THE REPUBLIC", y, fonts["small"], (100, 100, 100))
    y += 28
    draw_centered(draw, "MINISTRY OF EDUCATION", y, fonts["small"], (100, 100, 100))
    y += 44
    hline(draw, y, (30, 30, 30), width=2, margin=40)
    y += 20

    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["title"], W - 120):
        y += draw_centered(draw, ln, y, fonts["title"], TEXT_BLACK) + 6
    y += 18

    hline(draw, y, B2, width=1, margin=40)
    y += 28

    draw_centered(draw, "CERTIFICATE OF DEGREE", y, fonts["heading"], ACNT)
    y += 56

    draw_centered(draw, "Be it known that", y, fonts["body_italic"], TEXT_BLACK)
    y += 46

    y += draw_centered(draw, fields["student_name"].upper(), y, fonts["subtitle"], TEXT_BLACK) + 12

    hline(draw, y, B3, width=1, margin=180)
    y += 28

    y = draw_centered_wrapped(
        draw, "having satisfied all prescribed requirements, is hereby awarded the degree of",
        y, fonts["body"], TEXT_BLACK, W - 180,
    )
    y += 12

    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], TEXT_BLACK) + 8
    y += draw_centered(draw, f"in  {fields['specialization']}", y, fonts["body"], ACNT) + 20

    hline(draw, y, B3, width=1, margin=150)
    y += 16
    y += draw_centered(draw, f"Result: {fields['pass_class']}", y, fonts["heading"], TEXT_BLACK) + 30

    fy = H - 178
    hline(draw, fy, (30, 30, 30), width=3, margin=40)
    draw.text((60, fy + 20), "Signed:", font=fonts["small"], fill=(80, 80, 80))
    draw.text((60, fy + 42), fields["authority_name"], font=fonts["body"], fill=TEXT_BLACK)
    draw.text((60, fy + 72), f"Date: {fields['issue_date']}", font=fonts["body"], fill=TEXT_BLACK)
    cx, cy, r = W - 120, fy + 58, 56
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(30, 30, 30), width=3)
    draw.ellipse([cx-r+8, cy-r+8, cx+r-8, cy+r-8], outline=B2, width=1)
    draw_centered(draw, "OFFICIAL", cy - 8, fonts["small"], (30, 30, 30))

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 09 — Contemporary Blue
# ══════════════════════════════════════════════════════════════════════════════
def t09_contemporary_blue(fields: dict) -> Image.Image:
    """Light blue bg, colored top section, two-column detail table."""
    TOP   = (50, 90, 140)
    PANEL = (235, 245, 255)
    LABEL = (70, 100, 150)
    ACCENT = (70, 130, 200)

    img  = Image.new("RGB", (W, H), LIGHT_BLUE)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([0, 0, W, 200], fill=TOP)
    draw.rectangle([0, 200, W, 207], fill=BRIGHT_GOLD)
    draw.rectangle([40, 222, W - 40, H - 60], fill=PANEL, outline=ACCENT)

    y = 28
    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["subtitle"], W - 80):
        y += draw_centered(draw, ln, y, fonts["subtitle"], TEXT_WHITE) + 6
    y += 6
    draw_centered(draw, "Degree Certificate", y, fonts["body_italic"], BRIGHT_GOLD)
    y = 250

    draw_centered(draw, "This is to certify that", y, fonts["body_italic"], LABEL)
    y += 46

    h = draw_centered(draw, fields["student_name"], y, fonts["geo_title"], (20, 20, 80))
    y += h + 10
    nw = _tw(draw, fields["student_name"], fonts["geo_title"])
    draw.line([(W//2 - nw//2, y), (W//2 + nw//2, y)], fill=ACCENT, width=2)
    y += 28

    draw_centered(draw, "has been awarded", y, fonts["body_italic"], LABEL)
    y += 42

    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], (20, 20, 80)) + 6
    y += draw_centered(draw, f"in  {fields['specialization']}", y, fonts["body"], TEXT_BLACK) + 22

    hline(draw, y, ACCENT, width=1, margin=100)
    y += 22

    # Two-column detail block
    MID = W // 2
    for (ll, lv), (rl, rv) in zip(
        [("Class Awarded", fields["pass_class"]), ("Date of Issue", fields["issue_date"])],
        [("Authority", ""), ("", fields["authority_name"][:42])],
    ):
        draw.text((80, y),        ll + ":", font=fonts["label"], fill=LABEL)
        draw.text((80, y + 22),   lv,       font=fonts["value"], fill=TEXT_BLACK)
        if rl:
            draw.text((MID + 20, y),      rl + ":", font=fonts["label"], fill=LABEL)
        draw.text((MID + 20, y + 22), rv,           font=fonts["value"], fill=TEXT_BLACK)
        y += 62

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 10 — Heritage Brown
# ══════════════════════════════════════════════════════════════════════════════
def t10_heritage_brown(fields: dict) -> Image.Image:
    """Old-lace bg, thick golden-brown border, corner diamond accents."""
    BORDER = GOLDEN_BROWN
    INNER  = (180, 145, 30)
    TEXT   = (60, 35, 5)
    ACCENT = (100, 65, 10)

    img  = Image.new("RGB", (W, H), OLD_LACE)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([14, 14, W - 14, H - 14], outline=BORDER, width=7)
    draw.rectangle([28, 28, W - 28, H - 28], outline=INNER, width=1)
    for cx, cy in [(14, 14), (W - 14, 14), (14, H - 14), (W - 14, H - 14)]:
        s = 16
        draw.polygon([(cx, cy-s), (cx+s, cy), (cx, cy+s), (cx-s, cy)], fill=BORDER)

    y = 72
    draw_centered(draw, "CERTIFICATE OF DEGREE", y, fonts["heading"], INNER)
    y += 46
    double_hline(draw, y, BORDER, gap=10, w1=3, w2=1, margin=55)
    y += 36

    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["title"], W - 140):
        y += draw_centered(draw, ln, y, fonts["title"], TEXT) + 6
    y += 18

    double_hline(draw, y, BORDER, gap=10, w1=3, w2=1, margin=55)
    y += 36

    draw_centered(draw, "This is to certify that", y, fonts["body_italic"], ACCENT)
    y += 50

    y += draw_centered(draw, fields["student_name"], y, fonts["geo_title"], TEXT) + 18

    y = draw_centered_wrapped(
        draw, "has duly completed all requirements and is hereby conferred the degree of",
        y, fonts["body"], ACCENT, W - 200,
    )
    y += 10

    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], TEXT) + 6
    y += draw_centered(draw, f"in  {fields['specialization']}", y, fonts["body_italic"], ACCENT) + 22

    hline(draw, y, INNER, width=1, margin=150)
    y += 18
    y += draw_centered(draw, f"Class of Award:  {fields['pass_class']}", y, fonts["heading"], TEXT) + 55

    fy = H - 163
    hline(draw, fy, BORDER, width=3, margin=55)
    draw.text((80, fy + 18), fields["authority_name"], font=fonts["body"], fill=TEXT)
    ds = fields["issue_date"]
    draw.text((W - 90 - _tw(draw, ds, fonts["body"]), fy + 18), ds, font=fonts["body"], fill=TEXT)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 11 — Clean Modern
# ══════════════════════════════════════════════════════════════════════════════
def t11_clean_modern(fields: dict) -> Image.Image:
    """White bg, deep-blue accent top bar, fields as label / value rows."""
    TOP    = (0, 80, 160)
    DIVIDER= (220, 220, 230)
    LABEL  = (100, 100, 120)
    ACCENT = (0, 100, 200)

    img  = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([0, 0, W, 10],  fill=ACCENT)
    draw.rectangle([0, 10, W, 170], fill=TOP)
    draw.rectangle([0, 170, W, 178], fill=BRIGHT_GOLD)

    y = 22
    for ln in wrap_text(draw, fields["university_name"], fonts["subtitle"], W - 80):
        y += draw_centered(draw, ln, y, fonts["subtitle"], TEXT_WHITE) + 6
    draw_centered(draw, "DEGREE CERTIFICATE", y, fonts["small"], BRIGHT_GOLD)
    y = 200

    draw_centered(draw, "This is to certify that", y, fonts["body_italic"], LABEL)
    y += 46
    y += draw_centered(draw, fields["student_name"], y, fonts["geo_title"], (0, 50, 120)) + 28

    draw.line([(60, y), (W - 60, y)], fill=DIVIDER)
    y += 28

    LX, VX = 80, 300
    for lbl, val in [
        ("Degree Awarded",  fields["course_name"]),
        ("Specialization",  fields["specialization"]),
        ("Class of Award",  fields["pass_class"]),
        ("Issued On",       fields["issue_date"]),
        ("Authorised By",   fields["authority_name"]),
    ]:
        draw.text((LX, y), lbl, font=fonts["label"], fill=LABEL)
        for ln in wrap_text(draw, val, fonts["value"], W - VX - 80):
            draw.text((VX, y), ln, font=fonts["value"], fill=TEXT_BLACK)
            y += _th(draw, ln, fonts["value"]) + 4
        draw.line([(LX, y + 4), (W - LX, y + 4)], fill=DIVIDER)
        y += 22

    draw.rectangle([0, H - 10, W, H], fill=ACCENT)
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 12 — Prose Paragraph
# ══════════════════════════════════════════════════════════════════════════════
def t12_prose_paragraph(fields: dict) -> Image.Image:
    """Parchment bg, thin border, certificate as a single prose paragraph."""
    BORDER = (160, 140, 100)
    ACCENT = (80, 60, 20)

    img  = Image.new("RGB", (W, H), PARCHMENT)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([22, 22, W - 22, H - 22], outline=BORDER, width=2)

    y = 70
    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["title"], W - 140):
        y += draw_centered(draw, ln, y, fonts["title"], ACCENT) + 6
    y += 20
    hline(draw, y, BORDER, width=2, margin=70)
    y += 30

    draw_centered(draw, "CERTIFICATE OF DEGREE", y, fonts["heading"], ACCENT)
    y += 52

    prose = (
        f"This is to certify that {fields['student_name']} has successfully completed "
        f"the prescribed course of study for the degree of {fields['course_name']} "
        f"with a specialization in {fields['specialization']} and has been duly "
        f"awarded the said degree by {fields['university_name']} "
        f"with {fields['pass_class']}. "
        f"This certificate is issued in testimony thereof."
    )
    MG = 80
    for ln in wrap_text(draw, prose, fonts["geo_body"], W - 2 * MG):
        draw.text((MG, y), ln, font=fonts["geo_body"], fill=TEXT_DARK)
        y += _th(draw, ln, fonts["geo_body"]) + 10
    y += 36

    hline(draw, y, BORDER, width=1, margin=150)
    y += 26

    draw.text((MG, y), "Given under our hand and seal,", font=fonts["body_italic"], fill=ACCENT)
    y += 46
    draw.text((MG, y), fields["authority_name"], font=fonts["body"], fill=TEXT_DARK)
    ds = fields["issue_date"]
    draw.text((W - MG - _tw(draw, ds, fonts["body"]), y), ds, font=fonts["body"], fill=TEXT_DARK)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 13 — Split Banner
# ══════════════════════════════════════════════════════════════════════════════
def t13_split_banner(fields: dict) -> Image.Image:
    """Dark-blue banner top, white body, student name + degree centred."""
    img  = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([0, 0, W, 222], fill=DARK_BLUE)
    draw.rectangle([0, 222, W, 228], fill=BRIGHT_GOLD)

    y = 28
    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["subtitle"], W - 80):
        y += draw_centered(draw, ln, y, fonts["subtitle"], TEXT_WHITE) + 6
    y += 8
    draw_centered(draw, "CERTIFICATE OF DEGREE", y, fonts["heading"], BRIGHT_GOLD)
    y = 252

    draw_centered(draw, "AWARDED TO", y, fonts["small"], (120, 120, 130))
    y += 30

    y += draw_centered(draw, fields["student_name"], y, fonts["geo_title"], DARK_BLUE) + 18
    nw = _tw(draw, fields["student_name"], fonts["geo_title"])
    draw.line([(W//2 - nw//2, y), (W//2 + nw//2, y)], fill=BRIGHT_GOLD, width=2)
    y += 32

    y = draw_centered_wrapped(
        draw, "for the successful completion of the degree of",
        y, fonts["body_italic"], (100, 100, 100), W - 200,
    )
    y += 12

    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], DARK_BLUE) + 8
    y += draw_centered(draw, f"in  {fields['specialization']}", y, fonts["body"], TEXT_BLACK) + 26

    # Pass class badge
    draw.rectangle([W//2 - 180, y, W//2 + 180, y + 44], fill=DARK_BLUE)
    draw_centered(draw, f"  {fields['pass_class']}  ", y + 9, fonts["heading"], TEXT_WHITE)
    y += 44 + 42

    fy = H - 155
    draw.line([(60, fy), (W - 60, fy)], fill=(200, 200, 210))
    draw.text((80, fy + 20), fields["authority_name"], font=fonts["body"], fill=TEXT_BLACK)
    ds = fields["issue_date"]
    draw.text((W - 90 - _tw(draw, ds, fonts["body"]), fy + 20), ds, font=fonts["body"], fill=TEXT_BLACK)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 14 — Two Column
# ══════════════════════════════════════════════════════════════════════════════
def t14_two_column(fields: dict) -> Image.Image:
    """White bg, vertical center divider; left = institution+seal, right = student."""
    LEFT   = (245, 248, 252)
    BORDER = (180, 200, 220)
    ACCENT = (30, 70, 130)
    LABEL  = (80, 100, 140)
    SPLIT  = W // 2

    img  = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([0, 0, SPLIT, H], fill=LEFT)
    draw.rectangle([8, 8, W - 8, H - 8], outline=BORDER, width=2)
    draw.line([(SPLIT, 30), (SPLIT, H - 30)], fill=BORDER, width=2)
    draw.rectangle([8, 8, W - 8, 70], fill=ACCENT)
    draw_centered(draw, "DEGREE CERTIFICATE", 22, fonts["heading"], TEXT_WHITE)

    # Left panel
    y = 100
    draw.text((30, y), "Issued by:", font=fonts["small"], fill=LABEL)
    y += 22
    for ln in wrap_text(draw, fields["university_name"], fonts["subtitle"], SPLIT - 50):
        draw.text((30, y), ln, font=fonts["subtitle"], fill=ACCENT)
        y += _th(draw, ln, fonts["subtitle"]) + 5
    y += 18

    cx, cy, r = SPLIT // 2, y + 70, 60
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=ACCENT, width=3)
    draw.ellipse([cx-r+10, cy-r+10, cx+r-10, cy+r-10], outline=BORDER, width=1)
    draw_centered(draw, "SEAL", cy - 10, fonts["small"], ACCENT)
    y = cy + r + 28

    draw.text((30, y), "Authorised by:", font=fonts["small"], fill=LABEL)
    y += 22
    for ln in wrap_text(draw, fields["authority_name"], fonts["body"], SPLIT - 50):
        draw.text((30, y), ln, font=fonts["body"], fill=TEXT_BLACK)
        y += _th(draw, ln, fonts["body"]) + 4
    y += 14
    draw.text((30, y), f"Date: {fields['issue_date']}", font=fonts["body"], fill=TEXT_BLACK)

    # Right panel
    ry = 100
    draw.text((SPLIT + 30, ry), "Awarded to:", font=fonts["small"], fill=LABEL)
    ry += 28
    for ln in wrap_text(draw, fields["student_name"], fonts["subtitle"], SPLIT - 50):
        draw.text((SPLIT + 30, ry), ln, font=fonts["subtitle"], fill=(20, 20, 80))
        ry += _th(draw, ln, fonts["subtitle"]) + 5
    ry += 25

    for lbl, val in [
        ("Degree",         fields["course_name"]),
        ("Specialization", fields["specialization"]),
        ("Class Awarded",  fields["pass_class"]),
    ]:
        draw.text((SPLIT + 30, ry), lbl + ":", font=fonts["label"], fill=LABEL)
        ry += 22
        for ln in wrap_text(draw, val, fonts["value"], SPLIT - 55):
            draw.text((SPLIT + 30, ry), ln, font=fonts["value"], fill=TEXT_BLACK)
            ry += _th(draw, ln, fonts["value"]) + 4
        ry += 14

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 15 — Ribbon Formal
# ══════════════════════════════════════════════════════════════════════════════
def t15_ribbon_formal(fields: dict) -> Image.Image:
    """Cream bg, dark-goldenrod border, decorative ribbon band, formal centered."""
    BORDER   = DARK_GOLD
    RIBBON   = (210, 180, 50)
    RIBBON_BG = (255, 248, 210)
    ACCENT   = (130, 90, 0)

    img  = Image.new("RGB", (W, H), (255, 254, 245))
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([15, 15, W - 15, H - 15], outline=BORDER, width=5)
    draw.rectangle([24, 24, W - 24, H - 24], outline=(220, 190, 60), width=1)

    y = 65
    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["title"], W - 150):
        y += draw_centered(draw, ln, y, fonts["title"], TEXT_DARK) + 6
    y += 18

    # Top ribbon band
    draw.rectangle([40, y, W - 40, y + 50], fill=RIBBON_BG)
    draw.line([(40, y),      (W - 40, y)],      fill=RIBBON, width=3)
    draw.line([(40, y + 50), (W - 40, y + 50)], fill=RIBBON, width=3)
    draw_centered(draw, "CERTIFICATE OF DEGREE", y + 12, fonts["heading"], ACCENT)
    y += 50 + 32

    draw_centered(draw, "This is to certify that", y, fonts["body_italic"], ACCENT)
    y += 46

    h = draw_centered(draw, fields["student_name"], y, fonts["geo_title"], TEXT_DARK)
    y += h + 16
    nw = _tw(draw, fields["student_name"], fonts["geo_title"])
    draw.line([(W//2 - nw//2, y), (W//2 + nw//2, y)], fill=RIBBON, width=2)
    y += 28

    y = draw_centered_wrapped(
        draw, "has successfully fulfilled all requirements for the degree of",
        y, fonts["body"], ACCENT, W - 200,
    )
    y += 10

    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], TEXT_DARK) + 8
    y += draw_centered(draw, f"in  {fields['specialization']}", y, fonts["body_italic"], TEXT_DARK) + 26

    # Second ribbon accent (pass class)
    draw.rectangle([100, y, W - 100, y + 38], fill=RIBBON_BG)
    draw.line([(100, y),      (W - 100, y)],      fill=RIBBON, width=2)
    draw.line([(100, y + 38), (W - 100, y + 38)], fill=RIBBON, width=2)
    draw_centered(draw, f"Awarded with  {fields['pass_class']}", y + 8, fonts["heading"], ACCENT)
    y += 38 + 46

    fy = H - 163
    draw.line([(60, fy),     (W - 60, fy)],     fill=RIBBON,  width=2)
    draw.line([(60, fy + 5), (W - 60, fy + 5)], fill=BORDER, width=1)
    draw.text((85, fy + 20), fields["authority_name"], font=fonts["body"], fill=TEXT_DARK)
    ds = fields["issue_date"]
    draw.text((W - 95 - _tw(draw, ds, fonts["body"]), fy + 20), ds, font=fonts["body"], fill=TEXT_DARK)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template registry — import and reference this list in renderer.py
# ══════════════════════════════════════════════════════════════════════════════
TEMPLATES = [
    t01_classic_parchment,
    t02_modern_navy,
    t03_royal_burgundy,
    t04_emerald_formal,
    t05_minimalist_slate,
    t06_gold_ornate,
    t07_charcoal_silver,
    t08_government_official,
    t09_contemporary_blue,
    t10_heritage_brown,
    t11_clean_modern,
    t12_prose_paragraph,
    t13_split_banner,
    t14_two_column,
    t15_ribbon_formal,
    # NOTE: t16-t22 are appended at the bottom of this file,
    # after their function definitions, to avoid NameError at import time.
]


# ══════════════════════════════════════════════════════════════════════════════
#  Template 16 — Modern Purple (Bridify-style: colored bg, large italic name)
# ══════════════════════════════════════════════════════════════════════════════
def t16_modern_purple(fields: dict) -> Image.Image:
    """Deep purple bg, white/gold text, large italic student name."""
    BG      = (72, 32, 128)
    LIGHT   = (200, 180, 240)
    GOLD_L  = (255, 220, 100)
    WHITE   = (255, 255, 255)
    OFFWHITE= (240, 235, 255)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Decorative corner blocks
    for cx, cy in [(0, 0), (W, 0), (0, H), (W, H)]:
        x0 = max(0, cx - 100); y0 = max(0, cy - 100)
        x1 = min(W, cx + 100); y1 = min(H, cy + 100)
        draw.rectangle([x0, y0, x1, y1], fill=(55, 20, 100))

    y = 70
    draw_centered(draw, fields["university_name"].upper(), y, fonts["heading"], LIGHT)
    y += _th(draw, fields["university_name"], fonts["heading"]) + 26

    hline(draw, y, GOLD_L, width=2, margin=60)
    y += 20
    draw_centered(draw, "MASTER'S DEGREE CERTIFICATE", y, fonts["small"], GOLD_L)
    y += 36
    draw_centered(draw, "This is to certify that", y, fonts["body_italic"], OFFWHITE)
    y += 52

    # Large italic student name — the defining visual feature of modern certs
    h = draw_centered(draw, fields["student_name"], y, fonts["geo_title"], GOLD_L)
    y += h + 14
    nw = _tw(draw, fields["student_name"], fonts["geo_title"])
    draw.line([(W//2 - nw//2, y), (W//2 + nw//2, y)], fill=LIGHT, width=1)
    y += 28

    y = draw_centered_wrapped(
        draw,
        "as successfully completed all academic and professional requirements "
        "and is hereby awarded the degree of",
        y, fonts["body"], OFFWHITE, W - 200,
    )
    y += 12

    # Degree + specialization combined in one line (real-world style)
    degree_line = f"{fields['course_name']} in {fields['specialization']}"
    y += draw_centered(draw, degree_line, y, fonts["subtitle"], WHITE) + 10
    y = draw_centered_wrapped(
        draw, "with all rights, privileges, and honors duly conferred.",
        y, fonts["body_italic"], OFFWHITE, W - 200,
    )
    y += 14
    draw_centered(draw, f"Awarded on {fields['issue_date']}", y, fonts["body"], GOLD_L)
    y += _th(draw, fields["issue_date"], fonts["body"]) + 10
    draw_centered(draw, f"at {fields['university_name']}", y, fonts["small"], LIGHT)
    y += 48

    # Two-column authority
    parts = fields["authority_name"].split(", ", 1)
    title = parts[0] if len(parts) > 1 else "President"
    name  = parts[1] if len(parts) > 1 else fields["authority_name"]
    hline(draw, y, LIGHT, width=1, margin=80)
    y += 14
    draw.text((90,  y), name,    font=fonts["body"],  fill=WHITE)
    draw.text((90,  y + 26), title, font=fonts["small"], fill=LIGHT)
    draw.text((W - 300, y), "Department Chair", font=fonts["small"], fill=LIGHT)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 17 — Prose Certification ("We, the President...certify that")
# ══════════════════════════════════════════════════════════════════════════════
def t17_prose_certification(fields: dict) -> Image.Image:
    """Real Indian university style: full prose paragraph, italic student name,
    enrollment-style header, two signature blocks at bottom."""
    BG     = (255, 254, 248)
    BORDER = (60, 40, 10)
    ACCENT = (120, 80, 10)
    GOLD_L = WARM_GOLD
    TEXT   = (30, 20, 5)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts(scale=0.95)

    draw.rectangle([12, 12, W - 12, H - 12], outline=BORDER, width=4)
    draw.rectangle([22, 22, W - 22, H - 22], outline=GOLD_L, width=1)

    y = 68
    # Institution logo placeholder (circle)
    draw.ellipse([W//2 - 38, y, W//2 + 38, y + 76], outline=ACCENT, width=2)
    draw_centered(draw, "SEAL", y + 28, fonts["small"], ACCENT)
    y += 90

    for ln in wrap_text(draw, fields["university_name"], fonts["subtitle"], W - 140):
        y += draw_centered(draw, ln, y, fonts["subtitle"], ACCENT) + 5
    y += 12
    hline(draw, y, GOLD_L, width=2, margin=60)
    y += 20
    draw_centered(draw, "Degree Certificate", y, fonts["heading"], TEXT)
    y += 52

    # Full prose paragraph — "We, the President..."
    prose1 = (
        f"We, the President, the Executive President, the Vice Chancellor, "
        f"the Members of the Governing Body, the Board of Management and the "
        f"Academic Council of the {fields['university_name']}, certify that"
    )
    MG = 70
    for ln in wrap_text(draw, prose1, fonts["body"], W - 2 * MG):
        draw.text((MG, y), ln, font=fonts["body"], fill=TEXT)
        y += _th(draw, ln, fonts["body"]) + 8
    y += 14

    # Student name in large italic
    h = draw_centered(draw, fields["student_name"], y, fonts["geo_title"], TEXT)
    y += h + 6
    nw = _tw(draw, fields["student_name"], fonts["geo_title"])
    draw.line([(W//2 - nw//2, y), (W//2 + nw//2, y)], fill=GOLD_L, width=1)
    y += 24

    # Prose continuation
    prose2 = (
        f"has passed the requisite examination held in {fields['issue_date']} "
        f"as a regular student, with {fields['pass_class']}, and was found duly "
        f"qualified for the degree of"
    )
    for ln in wrap_text(draw, prose2, fonts["body"], W - 2 * MG):
        draw.text((MG, y), ln, font=fonts["body"], fill=TEXT)
        y += _th(draw, ln, fonts["body"]) + 8
    y += 10

    # Degree + specialization as the focal element
    degree_spec = f"{fields['course_name']}\n({fields['specialization']})"
    for ln in degree_spec.splitlines():
        fnt = fonts["geo_title"] if ln == degree_spec.splitlines()[0] else fonts["body_italic"]
        y += draw_centered(draw, ln, y, fnt, ACCENT) + 6
    y += 18

    # Two-column signature block
    fy = H - 160
    hline(draw, fy, GOLD_L, width=2, margin=60)
    parts = fields["authority_name"].split(", ", 1)
    lname = parts[1] if len(parts) > 1 else fields["authority_name"]
    ltitle= parts[0] if len(parts) > 1 else "Signing Authority"
    draw.text((MG,        fy + 18), lname,  font=fonts["body"],  fill=TEXT)
    draw.text((MG,        fy + 44), ltitle, font=fonts["small"], fill=ACCENT)
    draw.text((W - 300,   fy + 18), "President",     font=fonts["body"],  fill=TEXT)
    draw.text((W - 300,   fy + 44), "Vice-Chancellor", font=fonts["small"], fill=ACCENT)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 18 — Dark Navy Elegant
# ══════════════════════════════════════════════════════════════════════════════
def t18_dark_navy_elegant(fields: dict) -> Image.Image:
    """Dark navy background, gold + white text, formal centered layout."""
    BG    = (12, 24, 48)
    PANEL = (20, 38, 72)
    GOLD  = (212, 175, 55)
    WHITE = (255, 255, 255)
    CREAM = (240, 230, 200)
    LIGHT = (160, 180, 220)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([20, 20, W - 20, H - 20], outline=GOLD, width=2)
    draw.rectangle([28, 28, W - 28, H - 28], outline=(100, 80, 30), width=1)
    draw.rectangle([0, 0, W, 180], fill=PANEL)
    draw.line([(0, 180), (W, 180)], fill=GOLD, width=3)

    y = 28
    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["subtitle"], W - 100):
        y += draw_centered(draw, ln, y, fonts["subtitle"], GOLD) + 6
    draw_centered(draw, "DEGREE CERTIFICATE", y, fonts["small"], CREAM)
    y = 210

    draw_centered(draw, "This is to certify that", y, fonts["body_italic"], LIGHT)
    y += 46

    h = draw_centered(draw, fields["student_name"], y, fonts["geo_title"], WHITE)
    y += h + 12
    nw = _tw(draw, fields["student_name"], fonts["geo_title"])
    draw.line([(W//2 - nw//2, y), (W//2 + nw//2, y)], fill=GOLD, width=2)
    y += 30

    y = draw_centered_wrapped(
        draw, "has fulfilled all requirements and is awarded the degree of",
        y, fonts["body"], CREAM, W - 200,
    )
    y += 12

    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], GOLD) + 8
    y += draw_centered(draw, f"in  {fields['specialization']}", y, fonts["body"], CREAM) + 24

    hline(draw, y, GOLD, width=1, margin=160)
    y += 16
    if fields["pass_class"]:
        y += draw_centered(draw, f"Class of Award:  {fields['pass_class']}", y, fonts["heading"], WHITE) + 40

    fy = H - 155
    draw.line([(50, fy), (W - 50, fy)], fill=GOLD, width=2)
    draw.text((80, fy + 18), fields["authority_name"], font=fonts["body"], fill=WHITE)
    ds = fields["issue_date"]
    draw.text((W - 90 - _tw(draw, ds, fonts["body"]), fy + 18), ds, font=fonts["body"], fill=WHITE)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 19 — Teal Minimal Modern
# ══════════════════════════════════════════════════════════════════════════════
def t19_teal_minimal(fields: dict) -> Image.Image:
    """White bg, teal left stripe, very large student name, minimal lines."""
    TEAL   = (0, 128, 128)
    LTEAL  = (220, 245, 245)
    DARK   = (20, 20, 30)
    STRIPE = 14

    img  = Image.new("RGB", (W, H), (252, 252, 252))
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([0, 0, STRIPE, H], fill=TEAL)
    draw.rectangle([0, 0, W, STRIPE], fill=TEAL)
    draw.rectangle([W - STRIPE, 0, W, H], fill=TEAL)
    draw.rectangle([0, H - STRIPE, W, H], fill=TEAL)

    y = 70
    for ln in wrap_text(draw, fields["university_name"], fonts["subtitle"], W - 100):
        y += draw_centered(draw, ln, y, fonts["subtitle"], TEAL) + 6
    y += 10
    draw.line([(60, y), (W - 60, y)], fill=TEAL, width=2)
    y += 24
    draw_centered(draw, "DEGREE CERTIFICATE", y, fonts["heading"], DARK)
    y += 50

    draw_centered(draw, "This is to certify that", y, fonts["body_italic"], (100, 100, 110))
    y += 50

    # Very large student name — dominant visual element
    h = draw_centered(draw, fields["student_name"], y, fonts["geo_title"], TEAL)
    y += h + 18
    draw.line([(80, y), (W - 80, y)], fill=(220, 220, 220), width=1)
    y += 28

    y = draw_centered_wrapped(
        draw, "has successfully completed all requirements for",
        y, fonts["body"], (80, 80, 80), W - 200,
    )
    y += 10
    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], DARK) + 8
    y += draw_centered(draw, f"({fields['specialization']})", y, fonts["body_italic"], TEAL) + 24

    if fields["pass_class"]:
        draw.rectangle([W//2 - 170, y, W//2 + 170, y + 40], fill=LTEAL)
        draw_centered(draw, f"  {fields['pass_class']}  ", y + 8, fonts["heading"], TEAL)
        y += 60

    fy = H - 148
    draw.line([(60, fy), (W - 60, fy)], fill=TEAL, width=2)
    draw.text((80, fy + 16), fields["authority_name"], font=fonts["body"], fill=DARK)
    ds = fields["issue_date"]
    draw.text((W - 90 - _tw(draw, ds, fonts["body"]), fy + 16), ds, font=fonts["body"], fill=DARK)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 20 — Bottom Degree (degree name at bottom, student name middle)
# ══════════════════════════════════════════════════════════════════════════════
def t20_bottom_degree(fields: dict) -> Image.Image:
    """University+heading at top, student italic name at center,
    degree name in LARGE text at bottom — mimics many real university formats."""
    BORDER = (80, 40, 0)
    GOLD_L = WARM_GOLD
    ACCENT = (60, 30, 0)
    BG     = (255, 252, 245)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([14, 14, W - 14, H - 14], outline=BORDER, width=4)
    draw.rectangle([24, 24, W - 24, H - 24], outline=GOLD_L, width=1)

    # Logo placeholder
    y = 56
    draw.ellipse([W//2 - 36, y, W//2 + 36, y + 72], outline=ACCENT, width=2)
    y += 85

    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["subtitle"], W - 120):
        y += draw_centered(draw, ln, y, fonts["subtitle"], ACCENT) + 5
    y += 10
    hline(draw, y, GOLD_L, width=2, margin=60)
    y += 22

    draw_centered(draw, "Degree Certificate", y, fonts["heading"], BORDER)
    y += 52

    # Prose intro
    prose = (
        "We certify that"
    )
    draw_centered(draw, prose, y, fonts["body_italic"], ACCENT)
    y += 44

    # Student name in italic center
    h = draw_centered(draw, fields["student_name"], y, fonts["geo_title"], TEXT_DARK)
    y += h + 8
    nw = _tw(draw, fields["student_name"], fonts["geo_title"])
    draw.line([(W//2 - nw//2, y), (W//2 + nw//2, y)], fill=GOLD_L, width=2)
    y += 24

    draw_centered(draw, f"Enrollment No: MIT{fields['student_name'][:3].upper()}2024", y, fonts["small"], ACCENT)
    y += 30

    middle_prose = (
        f"has passed the examination with {fields['pass_class']} "
        f"and is hereby awarded the degree of"
    )
    for ln in wrap_text(draw, middle_prose, fonts["body"], W - 180):
        y += draw_centered(draw, ln, y, fonts["body"], ACCENT) + 8
    y += 18

    # DEGREE NAME as the largest text near the bottom — key feature
    for ln in wrap_text(draw, fields["course_name"], fonts["geo_title"], W - 120):
        y += draw_centered(draw, ln, y, fonts["geo_title"], BORDER) + 6
    y += draw_centered(draw, f"({fields['specialization']})", y, fonts["body_italic"], ACCENT) + 30

    fy = H - 150
    draw.line([(55, fy), (W - 55, fy)], fill=GOLD_L, width=2)
    parts = fields["authority_name"].split(", ", 1)
    lname  = parts[1] if len(parts) > 1 else fields["authority_name"]
    ltitle = parts[0] if len(parts) > 1 else "Authority"
    draw.text((80, fy + 16), lname,  font=fonts["body"],  fill=TEXT_DARK)
    draw.text((80, fy + 42), ltitle, font=fonts["small"], fill=ACCENT)
    ds = fields["issue_date"]
    draw.text((W - 90 - _tw(draw, ds, fonts["body"]), fy + 16), ds, font=fonts["body"], fill=TEXT_DARK)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 21 — Two-Column Authority Block
# ══════════════════════════════════════════════════════════════════════════════
def t21_two_col_authority(fields: dict) -> Image.Image:
    """Standard formal layout with explicit two-column signature block at bottom,
    each column has name + title (mimics real multi-signatory certificates)."""
    BORDER = NAVY
    GOLD_L = BRIGHT_GOLD
    ACCENT = (0, 45, 90)
    BG     = (251, 252, 255)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    draw.rectangle([14, 14, W - 14, H - 14], outline=BORDER, width=4)
    draw.rectangle([14, 14, W - 14, 190],     fill=BORDER)
    draw.line([(14, 190), (W - 14, 190)],     fill=GOLD_L, width=3)

    y = 28
    for ln in wrap_text(draw, fields["university_name"].upper(), fonts["subtitle"], W - 80):
        y += draw_centered(draw, ln, y, fonts["subtitle"], TEXT_WHITE) + 5
    draw_centered(draw, "CERTIFICATE OF DEGREE", y, fonts["small"], GOLD_L)
    y = 220

    draw_centered(draw, "This is to certify that", y, fonts["body_italic"], (80, 80, 90))
    y += 46
    h = draw_centered(draw, fields["student_name"], y, fonts["geo_title"], ACCENT)
    y += h + 12
    nw = _tw(draw, fields["student_name"], fonts["geo_title"])
    draw.line([(W//2 - nw//2, y), (W//2 + nw//2, y)], fill=GOLD_L, width=2)
    y += 28

    y = draw_centered_wrapped(
        draw, "has successfully completed the prescribed course and is awarded the degree of",
        y, fonts["body"], TEXT_BLACK, W - 200,
    )
    y += 10

    y += draw_centered(draw, fields["course_name"], y, fonts["subtitle"], BORDER) + 8
    y += draw_centered(draw, f"in  {fields['specialization']}", y, fonts["body_italic"], ACCENT) + 24

    hline(draw, y, GOLD_L, width=1, margin=150)
    y += 16
    if fields["pass_class"]:
        y += draw_centered(draw, f"Class of Award: {fields['pass_class']}", y, fonts["heading"], BORDER) + 16
    y += draw_centered(draw, f"Date: {fields['issue_date']}", y, fonts["body"], ACCENT) + 36

    # TWO-COLUMN authority block — explicit left and right signatories
    fy  = H - 165
    MID = W // 2
    draw.line([(60, fy), (MID - 20, fy)], fill=(180, 180, 200), width=1)
    draw.line([(MID + 20, fy), (W - 60, fy)], fill=(180, 180, 200), width=1)

    parts = fields["authority_name"].split(", ", 1)
    l_name  = parts[1] if len(parts) > 1 else fields["authority_name"]
    l_title = parts[0] if len(parts) > 1 else "Executive President"

    # Left signatory
    draw.text((70, fy + 12),  l_name,   font=fonts["body"],  fill=TEXT_BLACK)
    draw.text((70, fy + 38),  l_title,  font=fonts["small"], fill=ACCENT)
    draw.text((70, fy + 58),  "& Vice Chancellor", font=fonts["small"], fill=ACCENT)

    # Right signatory
    draw.text((MID + 30, fy + 12), "Prof. " + l_name.split()[-1], font=fonts["body"],  fill=TEXT_BLACK)
    draw.text((MID + 30, fy + 38), "President",   font=fonts["small"], fill=ACCENT)

    return img


# ══════════════════════════════════════════════════════════════════════════════
#  Template 22 — Colored Left Panel
# ══════════════════════════════════════════════════════════════════════════════
def t22_colored_panel(fields: dict) -> Image.Image:
    """Deep teal/green left panel with white text; white right body with details."""
    PANEL  = (20, 80, 80)
    PPANEL = (15, 60, 60)
    GOLD_L = (200, 170, 50)
    RIGHT  = (251, 253, 252)
    SPLIT  = int(W * 0.38)

    img  = Image.new("RGB", (W, H), RIGHT)
    draw = ImageDraw.Draw(img)
    fonts = get_fonts(scale=0.92)

    draw.rectangle([0, 0, SPLIT, H], fill=PANEL)
    draw.rectangle([SPLIT, 0, SPLIT + 6, H], fill=GOLD_L)

    # Left panel content
    y = 80
    for ln in wrap_text(draw, fields["university_name"], fonts["heading"], SPLIT - 40):
        draw.text((20, y), ln, font=fonts["heading"], fill=TEXT_WHITE)
        y += _th(draw, ln, fonts["heading"]) + 6
    y += 16
    draw.line([(20, y), (SPLIT - 20, y)], fill=GOLD_L, width=2)
    y += 24
    draw.text((20, y), "DEGREE", font=fonts["subtitle"], fill=GOLD_L)
    y += _th(draw, "DEGREE", fonts["subtitle"]) + 4
    draw.text((20, y), "CERTIFICATE", font=fonts["subtitle"], fill=GOLD_L)
    y += 60

    # Seal circle on left panel
    cxL = SPLIT // 2
    cyL = y + 70
    r   = 60
    draw.ellipse([cxL-r, cyL-r, cxL+r, cyL+r], outline=GOLD_L, width=3)
    draw.ellipse([cxL-r+10, cyL-r+10, cxL+r-10, cyL+r-10], outline=(150, 130, 50), width=1)
    draw.text((cxL - _tw(draw, "SEAL", fonts["small"]) // 2, cyL - 10), "SEAL", font=fonts["small"], fill=GOLD_L)
    y = cyL + r + 30

    draw.text((20, y), f"Date:", font=fonts["small"], fill=(180, 210, 210))
    y += 22
    for ln in wrap_text(draw, fields["issue_date"], fonts["body"], SPLIT - 30):
        draw.text((20, y), ln, font=fonts["body"], fill=TEXT_WHITE)
        y += _th(draw, ln, fonts["body"]) + 4

    # Right body content
    ry = 70
    RX = SPLIT + 30
    draw.text((RX, ry), "This is to certify that", font=fonts["body_italic"], fill=(100, 100, 110))
    ry += 44
    for ln in wrap_text(draw, fields["student_name"], fonts["geo_title"], W - RX - 30):
        draw.text((RX, ry), ln, font=fonts["geo_title"], fill=PANEL)
        ry += _th(draw, ln, fonts["geo_title"]) + 5
    ry += 20

    for lbl, val in [
        ("Degree",        fields["course_name"]),
        ("Specialization",fields["specialization"]),
        ("Class",         fields["pass_class"]),
    ]:
        draw.text((RX, ry), lbl + ":", font=fonts["label"], fill=(100, 100, 100))
        ry += 22
        for ln in wrap_text(draw, val, fonts["value"], W - RX - 30):
            draw.text((RX, ry), ln, font=fonts["value"], fill=TEXT_BLACK)
            ry += _th(draw, ln, fonts["value"]) + 4
        ry += 14

    ry += 20
    draw.line([(RX, ry), (W - 30, ry)], fill=(200, 200, 210))
    ry += 16
    draw.text((RX, ry), "Authorised by:", font=fonts["small"], fill=(120, 120, 130))
    ry += 22
    for ln in wrap_text(draw, fields["authority_name"], fonts["body"], W - RX - 30):
        draw.text((RX, ry), ln, font=fonts["body"], fill=TEXT_BLACK)
        ry += _th(draw, ln, fonts["body"]) + 4

    return img


# ── Append new templates after their definitions ──────────────────────────────
TEMPLATES.extend([
    t16_modern_purple,         # colored purple bg / large italic name
    t17_prose_certification,   # "We, the President...certify that" prose
    t18_dark_navy_elegant,     # dark navy bg / white/gold text
    t19_teal_minimal,          # teal accent / large name / minimal layout
    t20_bottom_degree,         # degree name at bottom in large bold
    t21_two_col_authority,     # two-column authority block at bottom
    t22_colored_panel,         # split colored left panel + white right
])

__all__ = ["TEMPLATES"]
