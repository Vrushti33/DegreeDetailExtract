"""Ceremonial prose generator for realistic degree certificate text — v3.

Provides 16 ceremonial prose templates (12 original + 4 new) that embed
all certificate fields inside natural, flowing language mimicking authentic
degree certificates.

Key v3 changes:
- ALL templates handle pass_class being empty (absent ~30% of the time)
- 4 new prose styles:
    13. prose_fully_cursive      — entire body in flowing script style
    14. prose_name_at_top        — name appears first, above all prose
    15. prose_label_value        — printed label:value pairs (South-Asian style)
    16. prose_gothic_proclamation — dramatic old-English blackletter style phrasing
"""

import random
from typing import List, NamedTuple


class ProseBlocks(NamedTuple):
    """Rendered text ready for certificate layout."""
    header_lines: List[str]      # institution name / title lines at top
    proclamation: str            # opening authority statement (italic)
    recipient_label: str         # phrase preceding the name
    body_paragraphs: List[str]   # paragraphs wrapping degree / specialization
    award_line: str              # "Awarded with First Class" — empty if no pass_class
    closing_lines: List[str]     # closing phrases before signature block
    # Extra layout hints (v3)
    name_at_top: bool = False    # if True, render name BEFORE proclamation
    all_cursive: bool = False    # if True, use script/cursive font for entire body


# ── Helpers ───────────────────────────────────────────────────────────────────

def _his_her() -> str:
    return random.choice(["his", "her", "their"])


def _him_her() -> str:
    return random.choice(["him", "her", "them"])


def _pass_suffix(fields: dict) -> str:
    """Return the pass-class fragment, or empty string if absent."""
    pc = fields.get("pass_class", "")
    if not pc:
        return ""
    return f" with {pc}"


def _pass_award_line(fields: dict) -> str:
    pc = fields.get("pass_class", "")
    if not pc:
        return ""
    return f"CLASS OF AWARD:  {pc.upper()}"


# ── Template 1 — President of Council proclamation ───────────────────────────
def prose_president_council(fields: dict) -> ProseBlocks:
    pc = _pass_suffix(fields)
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
                f"privileges, and responsibilities thereto appertaining{pc}. "
                f"The said degree is offered to {_him_her()} on {fields['issue_date']}."
            ),
        ],
        award_line=_pass_award_line(fields),
        closing_lines=[
            "In testimony whereof we have caused the seal of the University",
            "to be affixed and subscribed our hands on the date stated herein.",
        ],
    )


# ── Template 2 — Board of Management formal award ────────────────────────────
def prose_board_of_management(fields: dict) -> ProseBlocks:
    pc = _pass_suffix(fields)
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
                f"The Board is pleased to award {_him_her()} this degree{pc} "
                f"on {fields['issue_date']}."
            ),
        ],
        award_line=_pass_award_line(fields),
        closing_lines=[
            "Given under the authority of the Senate of the University.",
            "This certificate is issued subject to the regulations governing degrees.",
        ],
    )


# ── Template 3 — Chancellor's Conferral ──────────────────────────────────────
def prose_chancellor_conferral(fields: dict) -> ProseBlocks:
    pc = _pass_suffix(fields)
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
                f"this degree{pc}, "
                f"and the degree is offered on {fields['issue_date']}. "
                f"All the rights and privileges pertaining to this award are hereby granted."
            ),
        ],
        award_line=f"Conferred with:  {fields['pass_class']}" if fields.get("pass_class") else "",
        closing_lines=[
            f"Signed on behalf of the Chancellor,  {fields['university_name']}.",
        ],
    )


# ── Template 4 — Registrar's Academic Record ──────────────────────────────────
def prose_registrar(fields: dict) -> ProseBlocks:
    pc = fields.get("pass_class", "")
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
                + (f"in recognition of having passed the final university examinations "
                   f"with {pc}." if pc else
                   "in recognition of having passed the final university examinations.")
            ),
            (
                f"This certificate is issued by the Registrar's Office and constitutes "
                f"official proof of the above-mentioned academic qualification, "
                f"awarded on {fields['issue_date']}."
            ),
        ],
        award_line=f"Award Classification:  {pc}" if pc else "",
        closing_lines=[
            "This document bears the seal of the University and is valid without a signature.",
            "Any alteration renders this document null and void.",
        ],
    )


# ── Template 5 — Formal Proclamation ─────────────────────────────────────────
def prose_formal_proclamation(fields: dict) -> ProseBlocks:
    pc = _pass_suffix(fields)
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
            f"{fields['student_name']}",
            (
                f"the degree of {fields['course_name']} in {fields['specialization']}, "
                f"with all the rights, privileges, and responsibilities thereunto belonging. "
                f"The said degree is hereby offered to {_him_her()} on {fields['issue_date']}, "
                f"in recognition of {_his_her()} having passed all prescribed examinations{pc}."
            ),
        ],
        award_line=f"CLASS:  {fields['pass_class']}" if fields.get("pass_class") else "",
        closing_lines=[
            "In Witness Whereof, we have hereunto set our hands and caused",
            "the Seal of the University to be affixed.",
        ],
    )


# ── Template 6 — Senate Resolution ───────────────────────────────────────────
def prose_senate_resolution(fields: dict) -> ProseBlocks:
    pc = _pass_suffix(fields)
    award = fields.get("pass_class", "")
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
                f"be and is hereby awarded the said degree{pc}. "
                f"The degree takes effect from {fields['issue_date']} "
                f"and carries with it all academic privileges of this University."
            ),
        ],
        award_line=f"Senate Classification:  {award}" if award else "",
        closing_lines=[
            "Certified true extract from the minutes of the Academic Senate.",
        ],
    )


# ── Template 7 — Vice-Chancellor's Testimonial ───────────────────────────────
def prose_vice_chancellor(fields: dict) -> ProseBlocks:
    pc = _pass_suffix(fields)
    award = fields.get("pass_class", "")
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
                f"examinations of this University{pc}. "
                f"It is my privilege to award {_him_her()} this degree on {fields['issue_date']}."
            ),
        ],
        award_line=f"PASS WITH:  {award.upper()}" if award else "",
        closing_lines=[
            "The Vice-Chancellor's signature and University seal confirm this award.",
            "This certificate is issued under the authority of the University Act.",
        ],
    )


# ── Template 8 — Dean of Faculty Conferral ───────────────────────────────────
def prose_dean_faculty(fields: dict) -> ProseBlocks:
    pc = _pass_suffix(fields)
    award = fields.get("pass_class", "")
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
                f"The degree is conferred{pc} and is effective from {fields['issue_date']}."
            ),
        ],
        award_line=f"Awarded:  {award}" if award else "",
        closing_lines=[
            "This certificate is issued by authority of the Faculty Board.",
            "The University Seal and authorised signature authenticate this document.",
        ],
    )


# ── Template 9 — Terse British-style ─────────────────────────────────────────
def prose_british_terse(fields: dict) -> ProseBlocks:
    pc = _pass_suffix(fields)
    award = fields.get("pass_class", "")
    cl = f"Classification:  {award}. " if award else ""
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
        ],
        proclamation="The University hereby certifies that",
        recipient_label="",
        body_paragraphs=[
            (
                f"{fields['student_name']} has been awarded the degree of "
                f"{fields['course_name']} ({fields['specialization']}) "
                f"by {fields['university_name']}."
            ),
            (
                f"{cl}Date of award:  {fields['issue_date']}."
            ),
        ],
        award_line="",
        closing_lines=[
            f"Signed:  {fields['authority_name']}",
        ],
    )


# ── Template 10 — American-style Testimonial ──────────────────────────────────
def prose_american_testimonial(fields: dict) -> ProseBlocks:
    pc = _pass_suffix(fields)
    award = fields.get("pass_class", "")
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
                + (f"In recognition of {_his_her()} outstanding academic achievement, "
                   f"this degree is conferred{pc}." if award else
                   f"This degree is conferred in recognition of {_his_her()} academic achievement.")
            ),
            (
                f"Given at {fields['university_name']} this {fields['issue_date']}."
            ),
        ],
        award_line=f"Honor:  {award}" if award else "",
        closing_lines=[
            "By order of the Board of Trustees.",
        ],
    )


# ── Template 11 — South Asian University style ────────────────────────────────
def prose_south_asian(fields: dict) -> ProseBlocks:
    pc = fields.get("pass_class", "")
    pass_line = (f"The student appeared in the final university examination and "
                 f"passed with {pc}. " if pc else
                 "The student appeared in the final university examination and passed. ")
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
            f"Name of the Candidate:   {fields['student_name']}",
            (
                f"Degree Awarded:   {fields['course_name']}\n"
                f"Specialization:   {fields['specialization']}"
            ),
            (
                pass_line +
                f"The said degree is hereby offered to {_him_her()} on {fields['issue_date']}."
            ),
        ],
        award_line=f"Result of Final Examination:  {pc}" if pc else "",
        closing_lines=[
            f"Issued by the Office of the Controller of Examinations, {fields['university_name']}.",
            "This is a computer-generated certificate. No signature required.",
        ],
    )


# ── Template 12 — Declaratory (passive voice) ─────────────────────────────────
def prose_declaratory(fields: dict) -> ProseBlocks:
    pc = _pass_suffix(fields)
    award = fields.get("pass_class", "")
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
                f"having been examined and found to have passed{pc}."
            ),
            (
                "The degree carries all academic rights and privileges as defined by "
                "the University statutes in force at the time of award."
            ),
        ],
        award_line=f"Class of Pass:  {award}" if award else "",
        closing_lines=[
            "This document is authenticated by the University seal.",
            f"Authorised by: {fields['authority_name']}",
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
#  NEW v3 Prose Templates (13–16)
# ─────────────────────────────────────────────────────────────────────────────

# ── Template 13 — Fully-cursive flowing text ─────────────────────────────────
def prose_fully_cursive(fields: dict) -> ProseBlocks:
    """All text intended to be rendered in script/cursive font.
    Simulates old handwritten or copper-plate printed diplomas."""
    pc = _pass_suffix(fields)
    award = fields.get("pass_class", "")
    return ProseBlocks(
        header_lines=[
            fields["university_name"],
            "Certificate of Degree",
        ],
        proclamation=(
            f"This is to certify that"
        ),
        recipient_label="",
        body_paragraphs=[
            f"{fields['student_name']}",
            (
                f"having duly completed the course of study leading to the degree of "
                f"{fields['course_name']} in {fields['specialization']}, "
                f"and having passed all the prescribed examinations{pc}, "
                f"is hereby admitted to the said degree on {fields['issue_date']}."
            ),
            (
                f"In witness whereof the seal of {fields['university_name']} "
                f"is hereto affixed."
            ),
        ],
        award_line=f"Awarded:  {award}" if award else "",
        closing_lines=[
            f"Signed,  {fields['authority_name']}",
        ],
        all_cursive=True,
    )


# ── Template 14 — Name at very top ───────────────────────────────────────────
def prose_name_at_top(fields: dict) -> ProseBlocks:
    """Student name appears prominently at the top, above all prose text.
    Common in Australian and European university certificates."""
    pc = _pass_suffix(fields)
    award = fields.get("pass_class", "")
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
        ],
        proclamation="",
        recipient_label="",
        body_paragraphs=[
            (
                f"This is to certify that the undermentioned person has successfully "
                f"completed all the requirements for the degree of "
                f"{fields['course_name']} in {fields['specialization']} "
                f"as prescribed by {fields['university_name']}."
            ),
            (
                f"The degree is conferred{pc} "
                f"and is effective from {fields['issue_date']}. "
                f"All rights and privileges of the said degree are hereby granted."
            ),
        ],
        award_line=f"RESULT:  {award.upper()}" if award else "",
        closing_lines=[
            f"Authorised by: {fields['authority_name']}",
            f"{fields['university_name']}",
        ],
        name_at_top=True,
    )


# ── Template 15 — Label-value pairs (South Asian printed style) ───────────────
def prose_label_value_block(fields: dict) -> ProseBlocks:
    """Label:value tabular layout common on Indian university printed certificates.
    Each field on its own line in a structured block."""
    pc = fields.get("pass_class", "")
    rows = [
        f"Name of Student       :  {fields['student_name']}",
        f"University            :  {fields['university_name']}",
        f"Degree Conferred      :  {fields['course_name']}",
        f"Specialization        :  {fields['specialization']}",
        f"Date of Award         :  {fields['issue_date']}",
    ]
    if pc:
        rows.append(f"Class / Division      :  {pc}")
    rows.append(f"Authorised By         :  {fields['authority_name']}")

    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            "DEGREE CERTIFICATE",
        ],
        proclamation=(
            "This is to certify that the candidate whose particulars are given below "
            "has been awarded the degree as specified hereunder:"
        ),
        recipient_label="",
        body_paragraphs=rows,
        award_line="",
        closing_lines=[
            "This certificate is issued by the University and is subject to verification.",
            "Date of issue: " + fields["issue_date"],
        ],
    )


# ── Template 16 — Gothic/Old-English proclamation ────────────────────────────
def prose_gothic_proclamation(fields: dict) -> ProseBlocks:
    """Dramatic phrasing suited to blackletter/gothic title banners.
    Common in old European and some Indian residential university diplomas."""
    pc = _pass_suffix(fields)
    award = fields.get("pass_class", "")
    return ProseBlocks(
        header_lines=[
            fields["university_name"].upper(),
            "By Authority of the Chancellor and Senate",
            "BE IT KNOWN TO ALL",
        ],
        proclamation=(
            f"Whereas the Senate of {fields['university_name']}, having considered the record "
            f"of study and the results of examination duly held,"
        ),
        recipient_label="Has resolved to confer upon",
        body_paragraphs=[
            f"{fields['student_name']}",
            (
                f"the Degree of {fields['course_name']} in {fields['specialization']}, "
                f"together with all the honour, rights, and privileges thereunto appertaining. "
                f"The said degree is hereby offered{pc} "
                f"on the {fields['issue_date']}."
            ),
        ],
        award_line=f"Award:  {award}" if award else "",
        closing_lines=[
            "Given under the Seal of the University and the hand of the Chancellor.",
        ],
    )


# ── Registry — all 16 prose templates ────────────────────────────────────────
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
    # v3 additions:
    prose_fully_cursive,
    prose_name_at_top,
    prose_label_value_block,
    prose_gothic_proclamation,
]


def get_random_prose(fields: dict) -> ProseBlocks:
    """Return a randomly chosen ceremonial prose block for *fields*."""
    return random.choice(PROSE_TEMPLATES)(fields)


__all__ = ["ProseBlocks", "PROSE_TEMPLATES", "get_random_prose"]
