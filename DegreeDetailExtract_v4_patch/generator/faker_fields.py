"""Randomised field-value generation for synthetic degree certificates — v3.

Key improvements over v2:
- Rich textual/ordinal date formats: "15th day of June, 2002", "the 9th of July 2002"
- pass_class is OPTIONAL: absent ~30% of the time (as on real certs)
- Expanded pass_class vocabulary: 12 variants including Magna Cum Laude, Honours, etc.
- Generates a `has_pass_class` bool so templates know whether to render it
"""

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from faker import Faker

fake = Faker()

# ── pass_class: expanded, real-world vocabulary ───────────────────────────────
# v4: added Third Class / Division-style grades, which are extremely common on
# real Indian/Commonwealth-style degree certificates and were MISSING before —
# any real certificate using these terms was guaranteed to fail extraction.
PASS_CLASSES = [
    "Distinction",
    "First Class",
    "First Class with Distinction",
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
    "Pass with Credit",
    "Honours",
    "Merit",
    "Class II Division I",
    "Class II Division II",
    "Magna Cum Laude",
    "Summa Cum Laude",
    "With Credit",
]

# ── Degree names: (long form, short form) ────────────────────────────────────
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
]

# ── Specializations ───────────────────────────────────────────────────────────
SPECIALIZATIONS = [
    "Computer Science and Engineering",
    "Electronics and Communication Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Information Technology",
    "Electrical Engineering",
    "Chemical Engineering",
    "Biotechnology",
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
    "Aeronautical Engineering",
    "Instrumentation Engineering",
    "Food Technology",
    "Agricultural Science",
    "Microbiology",
    "Pharmacy",
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
]

# ── Signing authority titles ──────────────────────────────────────────────────
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
]


# ── Date generation helpers ───────────────────────────────────────────────────

_ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}

def _ordinal(n: int) -> str:
    """Return n with ordinal suffix: 1st, 2nd, 3rd, 4th, ..."""
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


def _format_date(dt: datetime) -> str:
    """Return the date in one of many real-world certificate date formats."""
    d, m, y = dt.day, dt.month, dt.year
    month_long  = _MONTH_NAMES[m - 1]
    month_short = _SHORT_MONTHS[m - 1]
    ord_d = _ordinal(d)

    formats = [
        # Numeric
        f"{d:02d}-{m:02d}-{y}",                           # 15-06-2002
        f"{d:02d}/{m:02d}/{y}",                            # 15/06/2002
        f"{m:02d}/{d:02d}/{y}",                            # 06/15/2002  (US)
        f"{y}-{m:02d}-{d:02d}",                            # 2002-06-15  (ISO)
        # Short textual
        f"{d} {month_long} {y}",                           # 15 June 2002
        f"{month_long} {d}, {y}",                          # June 15, 2002
        f"{d} {month_short} {y}",                          # 15 Jun 2002
        f"{month_short} {d}, {y}",                         # Jun 15, 2002
        f"{month_long} {y}",                               # June 2002
        # Ordinal textual — common on Indian/UK printed diplomas
        f"{ord_d} day of {month_long}, {y}",               # 15th day of June, 2002
        f"the {ord_d} day of {month_long} {y}",            # the 15th day of June 2002
        f"{month_long} {ord_d}, {y}",                      # June 15th, 2002
        f"{ord_d} {month_long} {y}",                       # 15th June 2002
        f"this {ord_d} of {month_long}, {y}",              # this 15th of June, 2002
        f"{ord_d} {month_short} {y}",                      # 15th Jun 2002
        f"{month_short}. {d}, {y}",                        # Jun. 15, 2002
        # Written-out year (rare but real)
        f"{d} {month_long}",                               # 15 June  (year elsewhere)
    ]
    return random.choice(formats)


_DATE_START      = datetime(1985, 1, 1)
_DATE_RANGE_DAYS = (datetime(2024, 12, 31) - _DATE_START).days

# ── Lazy-loaded university name list ──────────────────────────────────────────
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


# ── v4: OPEN-VOCABULARY university name generation ────────────────────────────
# Why this exists: with only ~85 fixed names (the old behaviour), each name was
# seen ~65 times across the dataset. That is few enough distinct values that the
# model can simply memorise "pick the closest of these 85 strings" instead of
# learning to genuinely read arbitrary text off the image. Any real university
# name not in that list (e.g. "University of Calicut") was structurally
# impossible to extract correctly. Mixing in procedurally generated, never-
# repeated names forces the model to actually read pixels instead of recalling
# a shortlist.
_UNIV_NAME_PATTERNS = [
    lambda: f"University of {fake.city()}",
    lambda: f"{fake.city()} University",
    lambda: f"{fake.last_name()} University",
    lambda: f"{fake.last_name()} Institute of Technology",
    lambda: f"{fake.city()} Institute of Technology",
    lambda: f"{fake.last_name()} College of "
            f"{random.choice(['Engineering', 'Arts and Science', 'Commerce', 'Medicine', 'Law'])}",
    lambda: f"{fake.state()} State University",
    lambda: f"National University of {fake.city()}",
    lambda: f"{fake.city()} Institute of "
            f"{random.choice(['Science', 'Technology', 'Management', 'Design'])}",
    lambda: f"{fake.last_name()}-{fake.last_name()} University",
]


def _random_university_name() -> str:
    """~50% curated real-ish names, ~50% procedurally generated & never repeated.

    The mix matters: curated names give the model realistic institution-name
    *style*, while the procedural half guarantees it can never simply memorise
    a closed set, since these are freshly random every call.
    """
    if random.random() < 0.50:
        return random.choice(_load_university_names())
    return random.choice(_UNIV_NAME_PATTERNS)()


# ── v4: VARIED authority_name formatting ───────────────────────────────────────
# Why this exists: the old code ALWAYS built this field as "{title}, {name}" —
# a single rigid shape across 100% of training examples. The model learned that
# shape as a hard rule rather than reading whatever is actually on the
# certificate (which might be just a title, just a name, or a different layout
# entirely — e.g. a "Vice Chancellor" label with a separately-placed signer
# name, as on many real certificates).
def _random_authority_name() -> str:
    title = random.choice(_AUTHORITY_TITLES)
    name = fake.name()
    fmt = random.choice([
        f"{title}, {name}",
        f"{name}, {title}",
        f"{name} ({title})",
        title,      # title only — common on real signature blocks
        name,       # name only
        f"{title}",
    ])
    return fmt


# ── Public API ────────────────────────────────────────────────────────────────

def generate_fields() -> Dict[str, str]:
    """Return a randomised dict of certificate fields.

    Keys
    ----
    student_name, university_name, course_name, specialization,
    pass_class   (empty string "" if absent — ~30% of the time),
    authority_name, issue_date.

    The caller should check ``bool(fields["pass_class"])`` before
    rendering it on the certificate.
    """
    degree_long, degree_short = random.choice(_DEGREES)
    # Long form 65%, short form 35%
    course_name = degree_long if random.random() > 0.35 else degree_short

    dt = _DATE_START + timedelta(days=random.randint(0, _DATE_RANGE_DAYS))
    issue_date = _format_date(dt)

    # pass_class: absent in ~30% of certificates
    if random.random() < 0.30:
        pass_class = ""
    else:
        pass_class = random.choice(PASS_CLASSES)

    return {
        "student_name":    fake.name(),
        "university_name": _random_university_name(),
        "course_name":     course_name,
        "specialization":  random.choice(SPECIALIZATIONS),
        "pass_class":      pass_class,
        "authority_name":  _random_authority_name(),
        "issue_date":      issue_date,
    }
