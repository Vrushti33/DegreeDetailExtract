"""Ceremonial prose generator for realistic degree certificate text.

Provides 12 ceremonial prose templates that embed all 7 certificate fields
inside natural, flowing language that mimics authentic degree certificates:
  - "We, the President of Council hereby award..."
  - "...the Board of Management certify that..."
  - "...having studied for the prescribed period..."
  - "...the degree is offered on..."
  - "...in recognition of having passed with [class]..."

Each template function returns a ``ProseBlocks`` namedtuple containing the
rendered text blocks ready for a Pillow drawing function to lay out.
"""

import random
from typing import List, NamedTuple


class ProseBlocks(NamedTuple):
    """Rendered text ready for certificate layout."""
    header_lines: List[str]          # institution name / title lines at top
    proclamation: str                # 1-2 sentence opening authority statement
    recipient_label: str             # phrase preceding the name ("This certifies that:")
    body_paragraphs: List[str]       # 1-3 paragraphs wrapping degree / specialization
    award_line: str                  # e.g. "Awarded with First Class Distinction"
    closing_lines: List[str]         # closing phrases before signature block


# ──────────────────────────────────────────────────────────────────────────────
#  Helper: pronoun selection
# ──────────────────────────────────────────────────────────────────────────────

def _his_her() -> str:
    return random.choice(["his", "her", "their"])


def _him_her() -> str:
    return random.choice(["him", "her", "them"])


# ──────────────────────────────────────────────────────────────────────────────
#  Prose Template 1 — President of Council proclamation
# ──────────────────────────────────────────────────────────────────────────────
def prose_president_council(fields: dict) -> ProseBlocks:
    pronoun = _his_her()
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            "OFFICE OF THE PRESIDENT & BOARD OF COUNCIL",
        ],
        proclamation=(
            "We, the President of the Council and the Board of Management of "
            f"{fields['university_name']}, acting by virtue of the authority vested "
            "in us by the Charter of this University, do hereby declare and proclaim:"
        ),
        recipient_label="THAT",
        body_paragraphs=[
            (
                f"{fields['student_name']}, having duly enrolled in the programme of study "
                f"and having satisfied all the prescribed requirements for the award of the "
                f"Degree of {fields['course_name']} with specialization in "
                f"{fields['specialization']},"
            ),
            (
                f"is hereby conferred the said degree, together with all the rights, "
                f"privileges, and responsibilities thereto appertaining. "
                f"The said degree is offered to {_him_her()} on {fields['issue_date']}."
            ),
        ],
        award_line=f"CLASS OF AWARD:  {fields['pass_class'].upper()}",
        closing_lines=[
            "In testimony whereof we have caused the seal of the University",
            "to be affixed and subscribed our hands on the date stated herein.",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Prose Template 2 — Board of Management formal award
# ──────────────────────────────────────────────────────────────────────────────
def prose_board_of_management(fields: dict) -> ProseBlocks:
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            "DEGREE AWARD CERTIFICATE",
        ],
        proclamation=(
            f"The Board of Management and Senate of {fields['university_name']} "
            "hereby certify, on the honour of this institution, that:"
        ),
        recipient_label="THE FOLLOWING CANDIDATE",
        body_paragraphs=[
            (
                f"{fields['student_name']} has been duly enrolled in the "
                f"{fields['course_name']} programme, "
                f"having studied for the full prescribed period in the discipline of "
                f"{fields['specialization']},"
            ),
            (
                f"and has been examined by the Board of Examiners and found to have "
                f"passed the final assessments in a manner satisfactory to the University. "
                f"The Board is pleased to award {_him_her()} this degree "
                f"on {fields['issue_date']}."
            ),
        ],
        award_line=f"Result:  {fields['pass_class']}",
        closing_lines=[
            "Given under the authority of the Senate of the University.",
            "This certificate is issued subject to the regulations governing degrees.",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Prose Template 3 — Chancellor's Conferral
# ──────────────────────────────────────────────────────────────────────────────
def prose_chancellor_conferral(fields: dict) -> ProseBlocks:
    pronoun = _his_her()
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            "THE CHANCELLOR'S OFFICE",
            "CERTIFICATE OF DEGREE CONFERRAL",
        ],
        proclamation=(
            "By virtue of the powers conferred upon the Chancellor by the Statutes "
            f"of {fields['university_name']}, and upon the recommendation of the "
            "Academic Council, this Certificate is issued."
        ),
        recipient_label="This is to certify that",
        body_paragraphs=[
            (
                f"{fields['student_name']} has successfully completed "
                f"all requirements for the degree of {fields['course_name']} "
                f"in {fields['specialization']}."
            ),
            (
                f"The Chancellor is pleased to confer upon {_him_her()} "
                f"this degree with {fields['pass_class']}, "
                f"and the degree is offered on {fields['issue_date']}. "
                f"All the rights and privileges pertaining to this award are hereby granted."
            ),
        ],
        award_line=f"Conferred with:  {fields['pass_class']}",
        closing_lines=[
            f"Signed on behalf of the Chancellor,  {fields['university_name']}.",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Prose Template 4 — Registrar's Academic Record
# ──────────────────────────────────────────────────────────────────────────────
def prose_registrar(fields: dict) -> ProseBlocks:
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            "ACADEMIC RECORDS AND CERTIFICATION DIVISION",
        ],
        proclamation=(
            f"The Registrar of {fields['university_name']} hereby certifies "
            "the following academic award as recorded in the official register of degrees:"
        ),
        recipient_label="Recipient:",
        body_paragraphs=[
            (
                f"{fields['student_name']} has been awarded the {fields['course_name']} "
                f"with specialization in {fields['specialization']}, "
                f"in recognition of having passed the final university examinations "
                f"with {fields['pass_class']}."
            ),
            (
                f"This certificate is issued by the Registrar's Office and constitutes "
                f"official proof of the above-mentioned academic qualification, "
                f"awarded on {fields['issue_date']}."
            ),
        ],
        award_line=f"Award Classification:  {fields['pass_class']}",
        closing_lines=[
            "This document bears the seal of the University and is valid without a signature.",
            "Any alteration renders this document null and void.",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Prose Template 5 — Formal Proclamation (short & centred)
# ──────────────────────────────────────────────────────────────────────────────
def prose_formal_proclamation(fields: dict) -> ProseBlocks:
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            "OFFICE OF ACADEMIC AFFAIRS",
        ],
        proclamation=(
            f"Know all persons by these presents that {fields['university_name']} "
            "has conferred upon:"
        ),
        recipient_label="",
        body_paragraphs=[
            (
                f"{fields['student_name']}"
            ),
            (
                f"the degree of {fields['course_name']} in {fields['specialization']}, "
                f"with all the rights, privileges, and responsibilities thereunto belonging. "
                f"The said degree is hereby offered to {_him_her()} on {fields['issue_date']}, "
                f"in recognition of {_his_her()} having passed all prescribed examinations."
            ),
        ],
        award_line=f"CLASS:  {fields['pass_class']}",
        closing_lines=[
            "In Witness Whereof, we have hereunto set our hands and caused",
            "the Seal of the University to be affixed.",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Prose Template 6 — Senate Resolution
# ──────────────────────────────────────────────────────────────────────────────
def prose_senate_resolution(fields: dict) -> ProseBlocks:
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            "RESOLUTION OF THE ACADEMIC SENATE",
        ],
        proclamation=(
            "At a duly convened meeting of the Academic Senate of "
            f"{fields['university_name']}, it was resolved to confer the following degree:"
        ),
        recipient_label="Resolved, that",
        body_paragraphs=[
            (
                f"{fields['student_name']}, having duly satisfied the academic "
                f"requirements for the programme of {fields['course_name']} "
                f"in the field of {fields['specialization']},"
            ),
            (
                f"be and is hereby awarded the said degree with the distinction of "
                f"{fields['pass_class']}. The degree takes effect from {fields['issue_date']} "
                f"and carries with it all academic privileges of this University."
            ),
        ],
        award_line=f"Senate Classification:  {fields['pass_class']}",
        closing_lines=[
            "Certified true extract from the minutes of the Academic Senate.",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Prose Template 7 — Vice-Chancellor's Testimonial
# ──────────────────────────────────────────────────────────────────────────────
def prose_vice_chancellor(fields: dict) -> ProseBlocks:
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            "OFFICE OF THE VICE-CHANCELLOR",
        ],
        proclamation=(
            f"I, {fields['authority_name']}, Vice-Chancellor of "
            f"{fields['university_name']}, do hereby certify that:"
        ),
        recipient_label="The undermentioned candidate,",
        body_paragraphs=[
            (
                f"{fields['student_name']}, has studied for the prescribed period "
                f"and completed the full course of instruction for the {fields['course_name']} "
                f"with specialization in {fields['specialization']}."
            ),
            (
                f"The said candidate has been duly examined and has passed the final "
                f"examinations of this University with {fields['pass_class']}. "
                f"It is my privilege to award {_him_her()} this degree on {fields['issue_date']}."
            ),
        ],
        award_line=f"PASS WITH:  {fields['pass_class'].upper()}",
        closing_lines=[
            "The Vice-Chancellor's signature and University seal confirm this award.",
            "This certificate is issued under the authority of the University Act.",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Prose Template 8 — Dean of Faculty Conferral
# ──────────────────────────────────────────────────────────────────────────────
def prose_dean_faculty(fields: dict) -> ProseBlocks:
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            f"FACULTY OF {fields['specialization'].upper()}",
            "CERTIFICATE OF COMPLETION",
        ],
        proclamation=(
            f"The Dean of the Faculty and the Examination Committee of "
            f"{fields['university_name']} hereby confirm the following academic award:"
        ),
        recipient_label="This is to certify that",
        body_paragraphs=[
            (
                f"{fields['student_name']} has been awarded the degree of "
                f"{fields['course_name']} in {fields['specialization']} "
                f"having fulfilled all academic and examination requirements "
                f"stipulated by this Faculty."
            ),
            (
                f"The degree is conferred with {fields['pass_class']} and is "
                f"effective from {fields['issue_date']}."
            ),
        ],
        award_line=f"Awarded:  {fields['pass_class']}",
        closing_lines=[
            "This certificate is issued by authority of the Faculty Board.",
            "The University Seal and authorised signature authenticate this document.",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Prose Template 9 — Terse British-style
# ──────────────────────────────────────────────────────────────────────────────
def prose_british_terse(fields: dict) -> ProseBlocks:
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
        ],
        proclamation=(
            "The University hereby certifies that"
        ),
        recipient_label="",
        body_paragraphs=[
            (
                f"{fields['student_name']} has been awarded the degree of "
                f"{fields['course_name']} ({fields['specialization']}) "
                f"by {fields['university_name']}."
            ),
            (
                f"Classification:  {fields['pass_class']}. "
                f"Date of award:  {fields['issue_date']}."
            ),
        ],
        award_line="",
        closing_lines=[
            f"Signed:  {fields['authority_name']}",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Prose Template 10 — American-style Testimonial
# ──────────────────────────────────────────────────────────────────────────────
def prose_american_testimonial(fields: dict) -> ProseBlocks:
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            "OFFICE OF THE PROVOST",
            "TESTIMONIAL OF DEGREE",
        ],
        proclamation=(
            f"The President, Trustees, and Faculty of {fields['university_name']} "
            "send greetings and hereby confer upon:"
        ),
        recipient_label="",
        body_paragraphs=[
            f"{fields['student_name']}",
            (
                f"the degree of {fields['course_name']} with a major in "
                f"{fields['specialization']}, with all the rights, privileges, "
                f"and responsibilities appertaining thereto. "
                f"In recognition of {_his_her()} outstanding academic achievement, "
                f"this degree is conferred with the honor of {fields['pass_class']}."
            ),
            (
                f"Given at {fields['university_name']} this {fields['issue_date']}."
            ),
        ],
        award_line=f"Honor:  {fields['pass_class']}",
        closing_lines=[
            "By order of the Board of Trustees.",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Prose Template 11 — South Asian University style
# ──────────────────────────────────────────────────────────────────────────────
def prose_south_asian(fields: dict) -> ProseBlocks:
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            "DEGREE CERTIFICATE",
            "Established under an Act of Parliament",
        ],
        proclamation=(
            f"This is to certify that the following student of "
            f"{fields['university_name']} has successfully completed the prescribed "
            f"course of study and examination and is hereby awarded the Degree mentioned below:"
        ),
        recipient_label="",
        body_paragraphs=[
            (
                f"Name of the Candidate:   {fields['student_name']}"
            ),
            (
                f"Degree Awarded:   {fields['course_name']}\n"
                f"Specialization:   {fields['specialization']}"
            ),
            (
                f"The student appeared in the final university examination and "
                f"passed with {fields['pass_class']}. "
                f"The said degree is hereby offered to {_him_her()} on {fields['issue_date']}."
            ),
        ],
        award_line=f"Result of Final Examination:  {fields['pass_class']}",
        closing_lines=[
            f"Issued by the Office of the Controller of Examinations, {fields['university_name']}.",
            "This is a computer-generated certificate. No signature required.",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Prose Template 12 — Declaratory (passive voice)
# ──────────────────────────────────────────────────────────────────────────────
def prose_declaratory(fields: dict) -> ProseBlocks:
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            "DECLARATION OF ACADEMIC ACHIEVEMENT",
        ],
        proclamation=(
            "It is hereby declared by the Academic Authority of "
            f"{fields['university_name']} that the degree stated herein has been "
            "duly awarded upon fulfilment of all statutory requirements:"
        ),
        recipient_label="Name of Awardee:",
        body_paragraphs=[
            f"{fields['student_name']}",
            (
                f"has been awarded the {fields['course_name']} "
                f"in {fields['specialization']} "
                f"by {fields['university_name']} on {fields['issue_date']}, "
                f"having been examined and found to have passed with {fields['pass_class']}."
            ),
            (
                "The degree carries all academic rights and privileges as defined by "
                "the University statutes in force at the time of award."
            ),
        ],
        award_line=f"Class of Pass:  {fields['pass_class']}",
        closing_lines=[
            "This document is authenticated by the University seal.",
            f"Authorised by: {fields['authority_name']}",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Registry — all 12 prose templates
# ──────────────────────────────────────────────────────────────────────────────
PROSE_TEMPLATES = [
    prose_president_council,
    prose_board_of_management,
    prose_chancellor_conferral,
    prose_registrar,
    prose_formal_proclamation,
    prose_senate_resolution,
    prose_vice_chancellor,
    prose_dean_faculty,
    prose_british_terse,
    prose_american_testimonial,
    prose_south_asian,
    prose_declaratory,
]


def get_random_prose(fields: dict) -> ProseBlocks:
    """Return a randomly chosen ceremonial prose block for *fields*."""
    return random.choice(PROSE_TEMPLATES)(fields)


__all__ = ["ProseBlocks", "PROSE_TEMPLATES", "get_random_prose"]
