"""
BrighterMonday job postings render a lot of their real content as plain,
consistently-labeled text rather than in distinct HTML elements -- easier
to pull out with a few well-anchored regexes than by guessing CSS classes
that may not exist. This module does that extraction against the fully
cleaned page text (see common.text_utils.clean_html).

Confirmed-live known vocabularies (job function categories, industries,
employment types) are used to split the "breadcrumb" line reliably, e.g.:

    "ACCOUNTANT ACCOUNTANT Anonymous Employer Accounting, Auditing & Finance
     2 weeks ago Easy apply ... Nairobi Full Time Banking, Finance & Insurance
     Confidential Share link Share on WhatsApp ..."

     -> company = "Anonymous Employer"
     -> function = "Accounting, Auditing & Finance"
     -> employment_type = "Full Time"
     -> industry = "Banking, Finance & Insurance"
     -> salary_range = "Confidential"

These lists were read off the live site (Sept 2026) and cover what's been
seen in scraped listings so far -- extend them if a new category, industry,
or location turns up in a future scrape (an unmatched value just means
that field comes back blank, nothing breaks).
"""

import re

FUNCTION_CATEGORIES = [
    "Accounting, Auditing & Finance", "Admin & Office", "Building & Architecture",
    "Creative & Design", "Customer Service & Support", "Engineering & Technology",
    "Health & Safety", "Human Resources", "Management & Business Development",
    "Marketing & Communications", "Medical & Pharmaceutical",
    "Research, Teaching & Training", "Sales", "Shipping & Logistics",
    "Supply Chain & Procurement",
]

INDUSTRIES = [
    "Advertising, Media & Communications", "Automotive & Aviation",
    "Banking, Finance & Insurance", "Construction", "Education",
    "Energy & Utilities", "Enforcement & Security", "Healthcare",
    "Hospitality & Hotel", "IT & Telecoms", "Manufacturing & Warehousing",
    "NGO, NPO & Charity", "Recruitment", "Retail, Fashion & FMCG",
    "Shipping & Logistics",
]

EMPLOYMENT_TYPES = ["Full Time", "Part Time", "Contract", "Internship & Graduate"]

# Sorted longest-first so regex alternation prefers the more specific match
# (e.g. "Research, Teaching & Training" before a shorter partial overlap).
_FUNCTION_ALT = "|".join(re.escape(f) for f in sorted(FUNCTION_CATEGORIES, key=len, reverse=True))
_TIME_AGO_RE = r"(?:Today|Yesterday|\d+\s+(?:day|days|week|weeks|month|months)\s+ago)"


def extract_company_and_function(text: str, title: str) -> tuple[str, str]:
    """Pull company name and job function from the repeated-title breadcrumb.

    Pattern: "<TITLE> <TITLE> <COMPANY> <FUNCTION> <TIME_AGO>"
    Returns ("", "") if the pattern isn't found (e.g. title has regex-special
    characters that don't escape cleanly, or the page structure differs).
    """
    if not title:
        return "", ""
    pattern = (
        re.escape(title) + r"\s+" + re.escape(title) +
        r"\s+(.*?)\s+(" + _FUNCTION_ALT + r")\s+" + _TIME_AGO_RE
    )
    match = re.search(pattern, text)
    if not match:
        return "", ""
    company = match.group(1).strip()
    function = match.group(2).strip()
    return company, function


def extract_labeled_field(text: str, label: str, stop_labels: list[str]) -> str:
    """Extract the value following a 'Label: value' marker, stopping at the
    next known label or a reasonable field-length cap."""
    stop_pattern = "|".join(re.escape(s) for s in stop_labels)
    pattern = re.escape(label) + r":\s*(.*?)(?=\s+(?:" + stop_pattern + r")|$)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


# The consistent metadata block: "Min Qualification: X Experience Level: Y
# Experience Length: Z Language Requirement: W Working Hours: V Applicant
# Location: U". Not every posting has every field (e.g. some omit Min
# Qualification), so each extraction stops at whichever label comes next.
METADATA_LABELS = [
    "Min Qualification", "Experience Level", "Experience Length",
    "Language Requirement", "Working Hours", "Applicant Location",
]


def extract_metadata_block(text: str) -> dict:
    fields = {}
    for label in METADATA_LABELS:
        other_labels = [l for l in METADATA_LABELS if l != label]
        # Also stop at "Job descriptions & requirements", which reliably
        # follows this block.
        fields[label] = extract_labeled_field(
            text, label, other_labels + ["Job descriptions & requirements"]
        )
    return fields


def extract_main_description(text: str) -> str:
    """The real job content sits between these two consistently-present
    markers. Falls back to the full text if either marker is missing."""
    start_marker = "Job descriptions & requirements"
    end_markers = ["Log In and Apply", "Important safety tips"]

    start_idx = text.find(start_marker)
    if start_idx == -1:
        return text
    start_idx += len(start_marker)

    end_idx = len(text)
    for marker in end_markers:
        idx = text.find(marker, start_idx)
        if idx != -1:
            end_idx = min(end_idx, idx)

    return text[start_idx:end_idx].strip()


def extract_salary_and_industry(text: str) -> tuple[str, str]:
    """Salary and industry sit in the badge row right before the
    'Share link Share on WhatsApp' anchor, e.g.:
    '... Nairobi Full Time Banking, Finance & Insurance Confidential
    Share link Share on WhatsApp ...'
    Only searches the text BEFORE the first 'Job descriptions &
    requirements' marker, so KSh figures mentioned inside the job body
    itself (e.g. a stipend amount) don't get mistaken for the salary badge.
    """
    boundary = text.find("Job descriptions & requirements")
    window = text[:boundary] if boundary != -1 else text[:800]

    industry = ""
    for ind in sorted(INDUSTRIES, key=len, reverse=True):
        if ind in window:
            industry = ind
            break

    salary = ""
    anchor = "Share link Share on WhatsApp"
    anchor_idx = window.find(anchor)
    if anchor_idx != -1:
        # Walk backward from the anchor to the end of whatever came before
        # it (industry name, employment type, or location) to isolate the
        # salary/"Confidential" token immediately preceding "Share link".
        preceding = window[:anchor_idx].rstrip()
        if industry and preceding.endswith(industry):
            salary = ""  # no salary token present, industry was the last thing
        else:
            ksh_match = re.search(
                r"(KSh[\sA-Za-z0-9,\.-]+|Confidential)\s*$",
                preceding,
            )
            if ksh_match:
                salary = ksh_match.group(1).strip()

    return salary, industry


def parse_brightermonday_text(full_text: str, title: str) -> dict:
    """Run all extractors and return a dict of the structured fields this
    module can pull out of a cleaned BrighterMonday detail-page text blob."""
    company, function = extract_company_and_function(full_text, title)
    metadata = extract_metadata_block(full_text)
    salary, industry = extract_salary_and_industry(full_text)
    description = extract_main_description(full_text)

    employment_type = ""
    working_hours = metadata.get("Working Hours", "")
    if working_hours:
        employment_type = working_hours.split(" - ")[0].strip()
        for known in EMPLOYMENT_TYPES:
            if working_hours.startswith(known):
                employment_type = known
                break

    required_experience = ""
    level = metadata.get("Experience Level", "")
    length = metadata.get("Experience Length", "")
    if level or length:
        required_experience = ", ".join(p for p in [level, length] if p)

    return {
        "company_profile": company,
        "function": function,
        "industry": industry,
        "salary_range": salary,
        "location": metadata.get("Applicant Location", ""),
        "employment_type": employment_type,
        "required_education": metadata.get("Min Qualification", ""),
        "required_experience": required_experience,
        "description": description,
    }
