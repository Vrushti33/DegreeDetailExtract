"""
Shared date utilities for v7 — handles all date formats found on real Indian/global
degree certificates, including the notoriously tricky written-out year format.

Used by:
  - generate_semi_synthetic_v7.py  (normalizing GT labels)
  - main_v7.py  (normalizing Donut predictions before display)
"""

import re
from datetime import datetime
from typing import Optional

# ── Word → number tables for written-out year parsing ─────────────────────────

_ONES_MAP = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19,
    # Ordinals
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
    "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
    "nineteenth": 19,
}

_TENS_MAP = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    # Ordinals
    "twentieth": 20, "thirtieth": 30, "fortieth": 40, "fiftieth": 50,
}

_MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    # Short forms
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
    # Common certificate typos/OCR errors
    "januray": 1, "janury": 1, "feburary": 2, "febuary": 2, "febrauary": 2,
    "septemer": 9, "septemeber": 9, "octomber": 10,
}


def _parse_words_year(text: str) -> Optional[int]:
    """
    Parse a written-out year like:
      "two thousand and twenty five"
      "two thousand twenty-five"
      "two thousand and nineteen"
      "two thousand"
    Returns an integer year (2000–2030) or None.
    """
    text = text.lower().strip()
    # Must start with "two thousand"
    if not text.startswith("two thousand"):
        return None

    remainder = text[len("two thousand"):].strip().lstrip("and").strip().lstrip("-").strip()
    if not remainder:
        return 2000

    # Try tens + ones ("twenty five", "twenty-five")
    remainder_norm = remainder.replace("-", " ").replace("  ", " ")
    parts = remainder_norm.split()

    if len(parts) == 1:
        word = parts[0]
        if word in _ONES_MAP:
            return 2000 + _ONES_MAP[word]
        if word in _TENS_MAP:
            return 2000 + _TENS_MAP[word]
    elif len(parts) == 2:
        tens_word, ones_word = parts[0], parts[1]
        if tens_word in _TENS_MAP and ones_word in _ONES_MAP:
            return 2000 + _TENS_MAP[tens_word] + _ONES_MAP[ones_word]

    return None


def _parse_ordinal_day(text: str) -> Optional[int]:
    """Parse '29th', '1st', '22nd', 'twenty ninth' → integer day."""
    text = text.strip().lower()

    # Numeric ordinal: "29th", "1st", "22nd", "3rd"
    m = re.match(r"(\d+)(?:st|nd|rd|th)?$", text)
    if m:
        return int(m.group(1))

    # Written-out ordinal (less common but present in some certs)
    _ORDINAL_MAP = {
        "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
        "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
        "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
        "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
        "nineteenth": 19, "twentieth": 20, "twenty first": 21, "twenty second": 22,
        "twenty third": 23, "twenty fourth": 24, "twenty fifth": 25,
        "twenty sixth": 26, "twenty seventh": 27, "twenty eighth": 28,
        "twenty ninth": 29, "thirtieth": 30, "thirty first": 31,
        # alternate spellings
        "twentyfirst": 21, "twentysecond": 22, "twentythird": 23,
        "twentyfourth": 24, "twentyfifth": 25, "twentysixth": 26,
        "twentyseventh": 27, "twentyeighth": 28, "twentyninth": 29,
    }
    if text in _ORDINAL_MAP:
        return _ORDINAL_MAP[text]

    return None


def normalize_date_to_ddmmyyyy(raw_date: str) -> str:
    """
    Normalize any date string to DD-MM-YYYY for the Donut ground-truth label.

    Handles:
      - DD-MM-YYYY, DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD
      - "24 July 2025", "July 24, 2025", "24 Jul 2025"
      - "24th July 2025", "24th day of July 2025"
      - "on the Twenty Ninth day of the month August in the year two thousand twenty five"
      - "on the 24th day of the month July, two thousand and twenty five"
      - "24th june 2020" (already user-normalized form from metadata.jsonl)
      - "2013" (year only → 01-01-2013)
      - "December 2010" (month+year → 01-12-2010)

    Falls back to returning raw_date if parsing fails.
    """
    raw = raw_date.strip()
    if not raw:
        return raw

    # ── Year-only ─────────────────────────────────────────────────────────────
    if re.fullmatch(r"\d{4}", raw):
        return f"01-01-{raw}"

    # ── Standard numeric / ISO formats ────────────────────────────────────────
    standard_patterns = [
        "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d",
        "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y",
        "%B %Y", "%b. %Y", "%b %Y",
        # ordinal textual with numeric day
        "%dth %B %Y", "%dst %B %Y", "%dnd %B %Y", "%drd %B %Y",
        "%dth %b %Y", "%dst %b %Y", "%dnd %b %Y", "%drd %b %Y",
        # "24th June 2020", "18th December 2024"  (user-normalized form)
        "%d %B %Y", "%d %b %Y",
    ]
    raw_stripped = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", raw, flags=re.IGNORECASE)
    for candidate in [raw, raw_stripped]:
        for fmt in standard_patterns:
            try:
                dt = datetime.strptime(candidate.strip(), fmt)
                return dt.strftime("%d-%m-%Y")
            except ValueError:
                continue

    # ── Ordinal numeric: "29th day of August, 2022" ───────────────────────────
    m = re.search(
        r"(\d+)(?:st|nd|rd|th)?\s+(?:day\s+of\s+(?:the\s+month\s+)?)?(\w+),?\s+(\d{4})",
        raw, re.IGNORECASE
    )
    if m:
        day, month_str, year = m.group(1), m.group(2), m.group(3)
        month_num = _MONTH_NAMES.get(month_str.lower())
        if month_num:
            try:
                return datetime(int(year), month_num, int(day)).strftime("%d-%m-%Y")
            except ValueError:
                pass

    # ── Written-out full date: "on the twenty ninth day of the month August,
    #    two thousand and twenty five" ─────────────────────────────────────────
    raw_lower = raw.lower()

    # Find month name
    found_month = None
    for month_word, month_num in _MONTH_NAMES.items():
        if re.search(r"\b" + re.escape(month_word) + r"\b", raw_lower):
            found_month = (month_word, month_num)
            break

    # Find year (numeric first, then written-out)
    year_val = None
    year_m = re.search(r"\b(19\d{2}|20\d{2})\b", raw)
    if year_m:
        year_val = int(year_m.group(1))
    else:
        # Written-out year — capture "two thousand and twenty five" etc.
        # Match: "two thousand" + optional "and" + optional tens-word + optional ones-word
        _tens_words = "twenty|twentieth|thirty|thirtieth|forty|fortieth|fifty|fiftieth|sixty|seventy|eighty|ninety"
        _ones_words = (
            "one|first|two|second|three|third|four|fourth|five|fifth|six|sixth|seven|seventh|"
            "eight|eighth|nine|ninth|ten|tenth|eleven|eleventh|twelve|twelfth|thirteen|thirteenth|"
            "fourteen|fourteenth|fifteen|fifteenth|sixteen|sixteenth|seventeen|seventeenth|"
            "eighteen|eighteenth|nineteen|nineteenth"
        )
        year_pattern = (
            r"(two\s+thousand"
            r"(?:\s+and)?"
            r"(?:\s+(?:" + _tens_words + r"))?"
            r"(?:[-\s]+(?:" + _ones_words + r"))?)"
        )
        year_phrase_m = re.search(year_pattern, raw_lower)
        if year_phrase_m:
            year_val = _parse_words_year(year_phrase_m.group(1))

    # Find day (numeric first, then written-out ordinal)
    day_val = None
    day_m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\b", raw, re.IGNORECASE)
    if day_m:
        day_val = int(day_m.group(1))
    else:
        # Written-out ordinal day: "twenty ninth", "eighteenth", etc.
        ordinal_chunk_m = re.search(
            r"\b((?:twenty|thirty)\s+\w+|\w+teenth|\w+th|\w+st|\w+nd|\w+rd|first|second|third|"
            r"fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)\b",
            raw_lower
        )
        if ordinal_chunk_m:
            day_val = _parse_ordinal_day(ordinal_chunk_m.group(1))

    if found_month and year_val and day_val:
        try:
            return datetime(year_val, found_month[1], day_val).strftime("%d-%m-%Y")
        except ValueError:
            pass

    # ── Last resort: just month + year ────────────────────────────────────────
    if found_month and year_val:
        try:
            return datetime(year_val, found_month[1], 1).strftime("%d-%m-%Y")
        except ValueError:
            pass

    # Fallback
    return raw
