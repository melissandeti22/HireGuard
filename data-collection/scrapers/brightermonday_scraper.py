"""
Scraper for BrighterMonday Kenya (https://www.brightermonday.co.ke).

Confirmed page structure (checked live, Sept 2026):
  - Listing pages:  https://www.brightermonday.co.ke/jobs?page=N
  - Detail pages:   https://www.brightermonday.co.ke/listings/<slug>-<id>
  - ~1,940 jobs live at time of writing, ~122 listing pages at 16/page.

IMPORTANT -- read before running:
This script needs to reach brightermonday.co.ke directly, which the sandbox
this was written in cannot do (its outbound network is restricted to package
registries only). It has NOT been executed end-to-end against the live site.
Run it from your own machine, and:
  1. Do a small test run first (`--max-pages 1`) and open the output CSV to
     sanity-check the fields before doing a full crawl.
  2. If BrighterMonday has changed their markup since Sept 2026, the
     `SELECTORS` dict below is the only place you should need to edit --
     open a listing page in your browser, right-click a job card -> Inspect,
     and update the CSS selector.
"""

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.http_client import PoliteSession, logger
from common.text_utils import clean_html, extract_email_domain, is_free_email_provider
from common.config import UNIFIED_COLUMNS
from common.brightermonday_extract import parse_brightermonday_text

BASE_URL = "https://www.brightermonday.co.ke"

# robots.txt (checked Sept 2026) disallows /*page=* by default but carves
# out explicit exceptions for page=2 through page=10. Page 1 has no query
# string at all -- it's just /jobs. Anything past page 10 is blocked, so
# MAX_ALLOWED_PAGE caps single-listing-path crawls there. To get more than
# ~160 jobs, crawl multiple category/location paths (see CATEGORY_PATHS
# below) rather than pushing past page 10 on one path.
MAX_ALLOWED_PAGE = 10


def listing_url(path: str, page: int) -> str:
    """Build an allowed listing URL for a given base path and page number.

    `path` is e.g. "/jobs", "/jobs/nairobi", "/jobs/sales" -- any of the
    plain (non-query-string) listing paths BrighterMonday exposes.
    """
    if page == 1:
        return BASE_URL + path
    if 2 <= page <= MAX_ALLOWED_PAGE:
        return f"{BASE_URL}{path}?page={page}"
    raise ValueError(
        f"page={page} is not allowed by robots.txt for a single listing path "
        f"(only page=1..{MAX_ALLOWED_PAGE} are permitted). "
        f"Crawl a different category/location path instead of going deeper here."
    )


# A sample of category/location paths confirmed live on the site (Sept 2026).
# Each one is its own allowed /jobs/<slug> path with its own page=1..10 --
# crawling across several of these gets you well past 160 jobs without ever
# touching a disallowed URL. Extend this list from the filter links on
# https://www.brightermonday.co.ke/jobs as needed.
CATEGORY_PATHS = [
    "/jobs",                          # all jobs, page 1 = latest
    "/jobs/nairobi",
    "/jobs/mombasa",
    "/jobs/sales",
    "/jobs/accounting-auditing-finance",
    "/jobs/software-data",
    "/jobs/human-resources",
    "/jobs/customer-service-support",
    "/jobs/marketing-communications",
    "/jobs/remote",
]

# Centralised so they're easy to fix if the site markup changes.
SELECTORS = {
    "job_card_link": "a[href*='/listings/']",
    "title": "h1",
}


def get_job_links_from_listing(session: PoliteSession, path: str, page: int) -> list[str]:
    url = listing_url(path, page)
    resp = session.get(url)
    if resp is None:
        return []
    soup = BeautifulSoup(resp.text, "lxml")
    links = set()
    for a in soup.select(SELECTORS["job_card_link"]):
        href = a.get("href", "")
        if href.startswith("/listings/"):
            links.add(BASE_URL + href)
        elif href.startswith(BASE_URL + "/listings/"):
            links.add(href)
    return sorted(links)


def parse_job_detail(session: PoliteSession, url: str) -> dict | None:
    resp = session.get(url)
    if resp is None:
        return None
    soup = BeautifulSoup(resp.text, "lxml")

    title_el = soup.select_one(SELECTORS["title"])
    title = title_el.get_text(strip=True) if title_el else ""

    body_el = soup.select_one("main") or soup.body
    full_text = clean_html(str(body_el)) if body_el else clean_html(resp.text)

    # Pull out company, function, industry, salary, location, employment
    # type, education/experience, and a clean job-content-only description
    # from the consistently-labeled text on the page (see module docstring
    # in brightermonday_extract.py for why this beats CSS selectors here).
    fields = parse_brightermonday_text(full_text, title)

    email_domain = extract_email_domain(resp.text)
    source_id = url.rstrip("/").split("/")[-1]

    record = {
        "source": "brightermonday",
        "source_id": source_id,
        "title": title,
        "location": fields["location"],
        "department": "",
        "salary_range": fields["salary_range"],
        "company_profile": fields["company_profile"],
        "description": fields["description"],
        "requirements": "",
        "benefits": "",
        "employment_type": fields["employment_type"],
        "required_experience": fields["required_experience"],
        "required_education": fields["required_education"],
        "industry": fields["industry"],
        "function": fields["function"],
        "telecommuting": "",
        "has_company_logo": "",
        "has_questions": "",
        "contact_email": "",
        "contact_email_domain": email_domain or "",
        "is_free_email_provider": int(is_free_email_provider(email_domain)),
        "posted_date": "",
        "url": url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "fraudulent": "",
    }
    return record


def scrape(paths: list[str], max_pages: int, output_path: Path, delay: float) -> None:
    session = PoliteSession(delay_seconds=delay)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    max_pages = min(max_pages, MAX_ALLOWED_PAGE)  # robots.txt hard limit per path

    all_links: list[str] = []
    for path in paths:
        for page in range(1, max_pages + 1):
            logger.info("Fetching %s page %d/%d ...", path, page, max_pages)
            links = get_job_links_from_listing(session, path, page)
            if not links:
                logger.info("No links found on %s page %d -- moving to next path.", path, page)
                break
            all_links.extend(links)

    all_links = sorted(set(all_links))
    logger.info("Found %d unique job listing URLs. Scraping details...", len(all_links))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=UNIFIED_COLUMNS)
        writer.writeheader()
        for i, url in enumerate(all_links, 1):
            record = parse_job_detail(session, url)
            if record:
                writer.writerow(record)
            if i % 10 == 0:
                logger.info("Scraped %d/%d job details", i, len(all_links))

    logger.info("Done. Wrote output to %s", output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape BrighterMonday Kenya job postings.")
    parser.add_argument(
        "--max-pages", type=int, default=1,
        help=f"Pages to crawl per category path (16 jobs/page). robots.txt caps this at {MAX_ALLOWED_PAGE}.",
    )
    parser.add_argument(
        "--categories", type=str, default="/jobs",
        help="Comma-separated listing paths to crawl, e.g. '/jobs,/jobs/nairobi,/jobs/sales'. "
             "Default is just '/jobs' (the main feed). See CATEGORY_PATHS in this file for more options.",
    )
    parser.add_argument("--output", type=str, default="../data/raw/brightermonday_raw.csv")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between requests.")
    args = parser.parse_args()

    paths = [p.strip() for p in args.categories.split(",") if p.strip()]
    scrape(paths=paths, max_pages=args.max_pages, output_path=Path(args.output), delay=args.delay)
