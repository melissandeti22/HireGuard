"""
Fuzu job detail pages are a React app styled with generated class names
(e.g. "sc-dHOixx dttzVk") that change between site builds, so CSS selectors
are fragile. The visible text, however, uses stable labels. Inside the
stable <section class="job-content"> container the text reads, line by line
(checked live, Oct 2026):

    ... Posted: 15 May 2025 | Apply by: 12 Jun 2025 | Expired
    Job details
    Location
    Nairobi
    •
    Kenya
    Contract Type
    [Full time]             <- often empty
    About the job
    Company
    Description
    <the actual job description, many lines>
    Tags
    Accounting, finance, banking, insurance
    Mid-level
    Kenya
    Start hiring with Fuzu
    ...

This module slices those lines by label, the same approach as
brightermonday_extract.py.
"""

import re

from bs4 import BeautifulSoup

from .text_utils import normalize_homoglyphs

EXPERIENCE_LEVELS = ["Entry level", "Entry-level", "Mid-level", "Mid level", "Senior", "Executive",
                     "Internship", "Graduate"]

_POSTED_RE = re.compile(r"Posted:\s*(\d{1,2}\s+\w+\s+\d{4})")
_APPLY_BY_RE = re.compile(r"Apply by:\s*(\d{1,2}\s+\w+\s+\d{4})")


def _lines(container) -> list[str]:
    text = normalize_homoglyphs(container.get_text("\n"))
    return [ln.strip() for ln in text.split("\n") if ln.strip()]


def _between(lines: list[str], start: str, stops: list[str], start_after: int = 0) -> tuple[list[str], int]:
    """Lines after the first `start` line (at or after `start_after`) up to the next stop line.
    Returns (lines, index of the start label) or ([], -1) if `start` is missing."""
    try:
        i = lines.index(start, start_after)
    except ValueError:
        return [], -1
    out = []
    for ln in lines[i + 1:]:
        if ln in stops:
            break
        out.append(ln)
    return out, i


def parse_fuzu_page(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    container = soup.select_one("section.job-content") or soup.select_one("main") or soup.body
    lines = _lines(container) if container else []
    flat = " ".join(lines)

    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""

    # The first company link is the (text-less) logo and a later one is the
    # "Company" tab; the header link in between carries the employer's name.
    company = ""
    for a in (container.select("a[href*='/company/']") if container else []):
        name = a.get_text(" ", strip=True).rstrip(", ")
        if name and name != "Company":
            company = name
            break

    # "Job details" block: Location, then optional Contract Type / Salary, then the tabs.
    detail_labels = ["Location", "Contract Type", "Salary", "About the job"]
    location_parts, _ = _between(lines, "Location", detail_labels)
    location = ", ".join(p for p in location_parts if p != "•")

    contract, _ = _between(lines, "Contract Type", detail_labels)
    employment_type = contract[0] if contract else ""

    salary, _ = _between(lines, "Salary", detail_labels)
    salary_range = " ".join(salary)

    # The description heading is the first "Description" after the "About the job" tab.
    about_idx = lines.index("About the job") if "About the job" in lines else 0
    desc_lines, desc_idx = _between(lines, "Description", ["Tags", "Start hiring with Fuzu"], about_idx)
    description = " ".join(desc_lines) if desc_idx != -1 else ""

    tags, _ = _between(lines, "Tags", ["Start hiring with Fuzu", "Job search tips from Fuzu"])
    # Level tags look like "Mid-level" or "Entry and Basic-level".
    level = next((t for t in tags if "level" in t.lower()
                  or any(t.lower() == lv.lower() for lv in EXPERIENCE_LEVELS)), "")
    categories = [t for t in tags if t != level and t != "Kenya"]

    posted = _POSTED_RE.search(flat)
    apply_by = _APPLY_BY_RE.search(flat)

    return {
        "title": title,
        "company_profile": company,
        "location": location,
        "employment_type": employment_type,
        "salary_range": salary_range,
        "required_experience": level,
        "function": categories[0] if categories else "",
        "industry": "; ".join(categories[1:]),
        "description": description,
        "posted_date": posted.group(1) if posted else "",
        "apply_by": apply_by.group(1) if apply_by else "",
        "is_job_page": bool(title and description),
    }
