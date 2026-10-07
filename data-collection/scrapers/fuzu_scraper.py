"""
Scraper for Fuzu Kenya (https://www.fuzu.com/kenya).

Confirmed page structure (checked live, Sept 2026):
  - Listing pages:   https://www.fuzu.com/kenya/job?page=N
  - Filtered views:  https://www.fuzu.com/kenya/job/<location-or-type-slug>
  - Detail pages:    linked from job cards on the listing pages (slug-based)

IMPORTANT -- read before running:
Same caveat as brightermonday_scraper.py: this could not be run against the
live site from the sandbox it was written in (outbound network there is
restricted to package registries only). Test with `--max-pages 1` first and
check the output CSV before doing a full crawl. If Fuzu's markup has
changed, the `SELECTORS` dict is the one place to edit -- inspect a job
card / detail page in your browser dev tools and update the CSS selector.
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

BASE_URL = "https://www.fuzu.com"
LISTING_URL_TEMPLATE = BASE_URL + "/kenya/job?page={page}"

SELECTORS = {
    "job_card_link": "a[href*='/kenya/job/']",
    "title": "h1",
    "company": "a[href*='/kenya/company/']",
}


def get_job_links_from_listing(session: PoliteSession, page: int) -> list[str]:
    url = LISTING_URL_TEMPLATE.format(page=page)
    resp = session.get(url)
    if resp is None:
        return []
    soup = BeautifulSoup(resp.text, "lxml")
    links = set()
    for a in soup.select(SELECTORS["job_card_link"]):
        href = a.get("href", "")
        # Filter out the category/filter links (e.g. /kenya/job/full-time),
        # keep only what look like individual job detail pages -- these
        # tend to have more path segments / a trailing job-id pattern.
        # Refine this once you've inspected the live markup.
        if href.count("/") >= 4:
            links.add(href if href.startswith("http") else BASE_URL + href)
    return sorted(links)


def parse_job_detail(session: PoliteSession, url: str) -> dict | None:
    resp = session.get(url)
    if resp is None:
        return None
    soup = BeautifulSoup(resp.text, "lxml")

    title_el = soup.select_one(SELECTORS["title"])
    title = title_el.get_text(strip=True) if title_el else ""

    company_el = soup.select_one(SELECTORS["company"])
    company = company_el.get_text(strip=True) if company_el else ""

    body_el = soup.select_one("main") or soup.body
    full_text = clean_html(str(body_el)) if body_el else clean_html(resp.text)

    email_domain = extract_email_domain(resp.text)
    source_id = url.rstrip("/").split("/")[-1]

    record = {
        "source": "fuzu",
        "source_id": source_id,
        "title": title,
        "location": "",
        "department": "",
        "salary_range": "",
        "company_profile": company,
        "description": full_text,
        "requirements": "",
        "benefits": "",
        "employment_type": "",
        "required_experience": "",
        "required_education": "",
        "industry": "",
        "function": "",
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


def scrape(max_pages: int, output_path: Path, delay: float) -> None:
    session = PoliteSession(delay_seconds=delay)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_links: list[str] = []
    for page in range(1, max_pages + 1):
        logger.info("Fetching listing page %d/%d ...", page, max_pages)
        links = get_job_links_from_listing(session, page)
        if not links:
            logger.info("No links found on page %d -- stopping pagination.", page)
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
    parser = argparse.ArgumentParser(description="Scrape Fuzu Kenya job postings.")
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--output", type=str, default="../data/raw/fuzu_raw.csv")
    parser.add_argument("--delay", type=float, default=3.0)
    args = parser.parse_args()

    scrape(max_pages=args.max_pages, output_path=Path(args.output), delay=args.delay)
