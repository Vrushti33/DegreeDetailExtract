"""Randomised field-value generation for synthetic degree certificates.

Generates realistic values for all 7 certificate fields using Faker
for names, a curated course/specialization vocabulary, and a fixed
closed-set vocabulary for pass_class.
"""

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from faker import Faker

fake = Faker()

# ── pass_class: confirmed closed-set vocabulary ────────────────────────────────
PASS_CLASSES = [
    "Distinction",
    "First Class",
    "Second Class Upper",
    "Second Class Lower",
    "Pass",
]

# ── Degree names: (long form, short form) ──────────────────────────────────────
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
    ("Master of Technology",                      "M.Tech."),
    ("Master of Science",                         "M.Sc."),
    ("Master of Business Administration",         "MBA"),
    ("Master of Arts",                            "M.A."),
    ("Master of Computer Applications",           "MCA"),
    ("Master of Commerce",                        "M.Com."),
    ("Doctor of Philosophy",                      "Ph.D."),
]

# ── Specializations ────────────────────────────────────────────────────────────
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
]

# ── Date formats for issue_date ────────────────────────────────────────────────
_DATE_FORMATS = [
    "%d %B %Y",    # 15 June 2023
    "%B %d, %Y",   # June 15, 2023
    "%d/%m/%Y",    # 15/06/2023
    "%d-%m-%Y",    # 15-06-2023
    "%B %Y",       # June 2023
    "%d %b %Y",    # 15 Jun 2023
]

_DATE_START     = datetime(2005, 1, 1)
_DATE_RANGE_DAYS = (datetime(2025, 12, 31) - _DATE_START).days

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


def generate_fields() -> Dict[str, str]:
    """Return a randomised dict of all 7 certificate fields.

    Returns
    -------
    Dict with keys: student_name, university_name, course_name,
    specialization, pass_class, authority_name, issue_date.
    """
    # Degree: use long form ~65% of the time, short form ~35%
    degree_long, degree_short = random.choice(_DEGREES)
    course_name = degree_long if random.random() > 0.35 else degree_short

    # Random issue date between 2005 and 2025
    issue_date = (
        _DATE_START + timedelta(days=random.randint(0, _DATE_RANGE_DAYS))
    ).strftime(random.choice(_DATE_FORMATS))

    authority_title = random.choice(_AUTHORITY_TITLES)

    return {
        "student_name":    fake.name(),
        "university_name": random.choice(_load_university_names()),
        "course_name":     course_name,
        "specialization":  random.choice(SPECIALIZATIONS),
        "pass_class":      random.choice(PASS_CLASSES),
        "authority_name":  f"{authority_title}, {fake.name()}",
        "issue_date":      issue_date,
    }
