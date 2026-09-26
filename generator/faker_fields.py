"""Randomised field-value generation for synthetic degree certificates — v5.

Key improvements over v4:
- Written-out year format: "the 15th day of the month June, two thousand and nineteen"
  (extremely common on Indian/South Asian printed diplomas; model was failing on these)
- authority_name: ~60% title-only (matches real certs where only "Vice-Chancellor" appears)
- specialization: empty for degree types that typically have none
  (BCA, BBA, B.Com, MBBS, B.Ed, LLB, B.Arch, MBA, MCA, Ph.D, M.D — matches real data)
- pass_class: expanded with grades like A+, A, O seen on real certs; absent ~35% of time
- University names updated with all 60 real cert universities added to curated list
- issue_date: ~15% year-only (e.g. "1997", "2013") — seen on several real certs
"""

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from faker import Faker

fake = Faker()

# ── pass_class: full real-world vocabulary (from real cert analysis) ──────────
# Added: A+, A, O, Pass Division, Third Division, First & Distinction,
# Honours Class I/II — all seen in the 60 real certificates labeled.
PASS_CLASSES = [
    "Distinction",
    "First Class",
    "First Class with Distinction",
    "First Class & Distinction",
    "Second Class Upper Division",
    "Second Class Lower Division",
    "Second Class",
    "Upper Second Class",
    "Third Class",
    "Third Division",
    "Second Division",
    "First Division",
    "Pass",
    "Pass Class",
    "Pass Division",
    "Pass with Credit",
    "Honours",
    "Honours Class I",
    "Merit",
    "Class II Division I",
    "Class II Division II",
    "Magna Cum Laude",
    "Summa Cum Laude",
    "With Credit",
    "A+",
    "A",
    "O",   # Outstanding — common on newer Indian university certificates
]

# Degrees that TYPICALLY have NO specialization on real certificates.
# When these are chosen, specialization is empty ~75% of the time.
_DEGREES_NO_SPEC = {
    "Bachelor of Computer Applications",
    "BCA",
    "Bachelor of Business Administration",
    "BBA",
    "Bachelor of Commerce",
    "B.Com.",
    "Bachelor of Medicine, Bachelor of Surgery",
    "MBBS",
    "Bachelor of Education",
    "B.Ed.",
    "Bachelor of Laws",
    "LL.B.",
    "Bachelor of Architecture",
    "B.Arch.",
    "Master of Business Administration",
    "MBA",
    "Master of Computer Applications",
    "MCA",
    "Master of Laws",
    "LL.M.",
    "Doctor of Philosophy",
    "Ph.D.",
    "Doctor of Medicine",
    "M.D.",
}

# ── Degree names: (long form, short form) ─────────────────────────────────────
_DEGREES = [
    ("Bachelor of Technology",                   "B.Tech."),
    ("Bachelor of Science",                       "B.Sc."),
    ("Bachelor of Commerce",                      "B.Com."),
    ("Bachelor of Arts",                          "B.A."),
    ("Bachelor of Engineering",                   "B.E."),
    ("Bachelor of Computer Applications",         "BCA"),
    ("Bachelor of Business Administration",       "BBA"),
    ("Bachelor of Medicine, Bachelor of Surgery", "MBBS"),
    ("Bachelor of Laws",                          "LL.B."),
    ("Bachelor of Education",                     "B.Ed."),
    ("Bachelor of Architecture",                  "B.Arch."),
    ("Bachelor of Fine Arts",                     "B.F.A."),
    ("Bachelor of Pharmacy",                      "B.Pharm."),
    ("Bachelor of Physiotherapy",                 "BPT"),
    ("Bachelor of Ayurvedic Medicine & Surgery",  "BAMS"),
    ("Master of Technology",                      "M.Tech."),
    ("Master of Science",                         "M.Sc."),
    ("Master of Business Administration",         "MBA"),
    ("Master of Arts",                            "M.A."),
    ("Master of Computer Applications",           "MCA"),
    ("Master of Commerce",                        "M.Com."),
    ("Master of Engineering",                     "M.E."),
    ("Master of Laws",                            "LL.M."),
    ("Doctor of Philosophy",                      "Ph.D."),
    ("Doctor of Medicine",                        "M.D."),
    ("Diploma in Engineering",                    "Diploma"),
]

# ── Specializations ────────────────────────────────────────────────────────────
SPECIALIZATIONS = [
    "Computer Science and Engineering",
    "Computer Science & Engineering",
    "Electronics and Communication Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Information Technology",
    "Electrical Engineering",
    "Electrical & Electronics Engineering",
    "Chemical Engineering",
    "Biotechnology",
    "Marine Engineering",
    "Aeronautical Engineering",
    "Data Science",
    "Artificial Intelligence and Machine Learning",
    "Finance",
    "Marketing",
    "Human Resource Management",
    "Physics",
    "Chemistry",
    "Mathematics",
    "Biology",
    "Environmental Science",
    "Economics",
    "English Literature",
    "History",
    "Psychology",
    "Architecture",
    "Instrumentation Engineering",
    "Food Technology",
    "Agricultural Science",
    "Microbiology",
    "Pharmacy",
    "Pharmaceutical Chemistry",
    "Operations Management",
    "Management Studies",
    "Business Analytics",
    "Journalism and Mass Communication",
    "Social Work",
    "Public Administration",
    "Nursing",
    "Dentistry",
    "Veterinary Science",
    "Hotel Management",
    "Textile Technology",
    "Nanotechnology",
    "General",
    "Chemistry, Botany, Biotechnology",
    "Film and Electronic Arts - Theory and Practice of Cinema",
    "Business Management (Economics)",
    "Animal Reproduction",
]

# ── Signing authority titles ───────────────────────────────────────────────────
_AUTHORITY_TITLES = [
    "Vice-Chancellor",
    "Registrar",
    "Controller of Examinations",
    "Dean of Academic Affairs",
    "Pro-Vice-Chancellor",
    "Academic Registrar",
    "Director of Studies",
    "Provost",
    "President",
    "Chancellor",
    "Principal",
    "Director",
    "Secretary",
    "Dean",
    "Rector",
]


# ── Date generation helpers ────────────────────────────────────────────────────

_ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}

def _ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{_ORDINAL_SUFFIXES.get(n % 10, 'th')}"


_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

_SHORT_MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# Written-out number words for years — common on Indian/South Asian certificates
# e.g. "two thousand and nineteen"
_ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
         "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
         "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _year_to_words(year: int) -> str:
    """Convert a year like 2019 -> 'two thousand and nineteen'."""
    if year < 2000 or year > 2030:
        return str(year)  # only handle modern years for simplicity
    remainder = year - 2000
    if remainder == 0:
        return "two thousand"
    if remainder < 20:
        return f"two thousand and {_ONES[remainder]}"
    tens, ones = divmod(remainder, 10)
    parts = [_TENS[tens]]
    if ones:
        parts.append(_ONES[ones])
    return "two thousand and " + " ".join(parts)


def _format_date(dt: datetime) -> str:
    """Return the date in one of many real-world certificate date formats."""
    d, m, y = dt.day, dt.month, dt.year
    month_long  = _MONTH_NAMES[m - 1]
    month_short = _SHORT_MONTHS[m - 1]
    ord_d = _ordinal(d)
    year_words = _year_to_words(y)

    formats = [
        # Numeric (most common on Indian certs)
        f"{d:02d}-{m:02d}-{y}",
        f"{d:02d}/{m:02d}/{y}",
        f"{m:02d}/{d:02d}/{y}",          # US style
        f"{y}-{m:02d}-{d:02d}",           # ISO
        # Short textual
        f"{d} {month_long} {y}",
        f"{month_long} {d}, {y}",
        f"{d} {month_short} {y}",
        f"{month_short} {d}, {y}",
        f"{month_long} {y}",             # month + year only
        f"{month_short}. {y}",
        # Ordinal textual
        f"{ord_d} day of {month_long}, {y}",
        f"the {ord_d} day of {month_long} {y}",
        f"{month_long} {ord_d}, {y}",
        f"{ord_d} {month_long} {y}",
        f"this {ord_d} of {month_long}, {y}",
        f"{ord_d} {month_short} {y}",
        # v5: WRITTEN-OUT year format — extremely common on Indian diplomas
        # These were confusing the model badly because it had never seen them
        f"on the {ord_d} day of the month {month_long}, {year_words}",
        f"the {ord_d} day of {month_long}, {year_words}",
        f"{ord_d} {month_long}, {year_words}",
        f"on {ord_d} {month_long} {year_words}",
        # Year-only (seen on ~10% of real certs when date unclear)
        str(y),
    ]
    # Year-only appears much less frequently — weight it low via sampling
    # (15% chance of year-only, 5% written-out, rest split normally)
    r = random.random()
    if r < 0.15:
        return str(y)
    if r < 0.25:
        # Written-out year format
        return random.choice([
            f"on the {ord_d} day of the month {month_long}, {year_words}",
            f"the {ord_d} day of {month_long}, {year_words}",
            f"{ord_d} {month_long}, {year_words}",
        ])
    return random.choice(formats[:-4])  # normal formats


_DATE_START      = datetime(1985, 1, 1)
_DATE_RANGE_DAYS = (datetime(2025, 12, 31) - _DATE_START).days

# ── University name list (curated from real certs + originals) ────────────────
_UNIVERSITY_NAMES = None


def _load_university_names():
    global _UNIVERSITY_NAMES
    if _UNIVERSITY_NAMES is None:
        path = Path(__file__).parent / "university_names.txt"
        with open(path, encoding="utf-8") as f:
            _UNIVERSITY_NAMES = [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ]
    return _UNIVERSITY_NAMES


# v5: Procedural university name patterns (broader than v4 — includes Indian styles)
_UNIV_NAME_PATTERNS = [
    lambda: f"University of {fake.city()}",
    lambda: f"{fake.city()} University",
    lambda: f"{fake.last_name()} University",
    lambda: f"{fake.last_name()} Institute of Technology",
    lambda: f"{fake.city()} Institute of Technology",
    lambda: f"{fake.last_name()} College of {random.choice(['Engineering', 'Arts and Science', 'Commerce', 'Medicine', 'Law', 'Nursing'])}",
    lambda: f"{fake.state()} State University",
    lambda: f"National University of {fake.city()}",
    lambda: f"{fake.city()} Institute of {random.choice(['Science', 'Technology', 'Management', 'Design'])}",
    lambda: f"{fake.last_name()}-{fake.last_name()} University",
    lambda: f"{fake.last_name()} Academy of {random.choice(['Higher Education and Research', 'Medical Sciences', 'Engineering', 'Management'])}",
    lambda: f"{fake.city()} College of {random.choice(['Arts', 'Science', 'Commerce', 'Engineering', 'Medicine'])}",
    lambda: f"Dr. {fake.last_name()} University",
    lambda: f"{fake.last_name()} Vidyapeeth",
    lambda: f"{fake.city()} Mahavidyalaya",
    lambda: f"Shri {fake.last_name()} Institute of {random.choice(['Technology', 'Management', 'Science'])}",
]


def _random_university_name() -> str:
    """~40% curated real names, ~60% procedurally generated."""
    if random.random() < 0.40:
        return random.choice(_load_university_names())
    return random.choice(_UNIV_NAME_PATTERNS)()


# ── v5: authority_name — title-only MUCH more common ──────────────────────────
# Real-world analysis: 54 out of 61 real certs had authority_name = "" or title-only.
# Only 7 had an actual person name. Training set MUST reflect this.
def _random_authority_name() -> str:
    title = random.choice(_AUTHORITY_TITLES)
    name = fake.name()
    r = random.random()
    if r < 0.60:
        return ""          # most common: no authority name extracted
    if r < 0.80:
        return title       # title only: "Vice-Chancellor"
    if r < 0.90:
        return f"{title}, {name}"
    if r < 0.95:
        return f"{name}, {title}"
    return name            # name only


# ── Public API ────────────────────────────────────────────────────────────────

def generate_fields() -> Dict[str, str]:
    """Return a randomised dict of certificate fields.

    Keys: student_name, university_name, course_name, specialization,
          pass_class (empty ~35% of time), authority_name, issue_date.
    """
    degree_long, degree_short = random.choice(_DEGREES)
    # Long form 65%, short form 35%
    course_name = degree_long if random.random() > 0.35 else degree_short

    # v5: specialization is empty for degrees that typically don't have it
    if course_name in _DEGREES_NO_SPEC and random.random() < 0.75:
        specialization = ""
    elif random.random() < 0.15:
        # Even for other degrees, ~15% have no specialization (General, Hons, etc.)
        specialization = ""
    else:
        specialization = random.choice(SPECIALIZATIONS)

    dt = _DATE_START + timedelta(days=random.randint(0, _DATE_RANGE_DAYS))
    issue_date = _format_date(dt)

    # pass_class: absent in ~35% of certificates
    if random.random() < 0.35:
        pass_class = ""
    else:
        pass_class = random.choice(PASS_CLASSES)

    return {
        "student_name":    fake.name(),
        "university_name": _random_university_name(),
        "course_name":     course_name,
        "specialization":  specialization,
        "pass_class":      pass_class,
        "authority_name":  _random_authority_name(),
        "issue_date":      issue_date,
    }
