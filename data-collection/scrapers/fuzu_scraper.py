"""
Scraper for Fuzu Kenya (https://www.fuzu.com/kenya).

Confirmed page structure (checked live, Oct 2026):
  - Job detail pages:  https://www.fuzu.com/kenya/jobs/<slug>
  - The /kenya/job?page=N listing pages render job cards with JavaScript, so
    their static HTML only contains category/location filter links
    (/kenya/job/<category>), not job links. Scraping those pages yields
    filter menus, not postings.
  - Fuzu's robots.txt advertises a job-listings sitemap instead:
      https://www.fuzu.com/kenya/sitemap-job-listings.xml.gz
    which indexes one sitemap per category, e.g.
      https://www.fuzu.com/kenya/sitemap-accounting-finance-listings.xml.gz
    Those list every job URL, including postings that have since expired
    (their text is still shown, marked "Closed for applications").

Job discovery therefore goes through the sitemaps; field extraction lives in
common/fuzu_extract.py. Test with a small --max-jobs first and check the
output CSV before doing a larger crawl.
"""

import argparse
import csv
import gzip
import re
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.http_client import PoliteSession, logger
from common.text_utils import extract_email_domain, is_free_email_provider
from common.config import UNIFIED_COLUMNS
from common.fuzu_extract import parse_fuzu_page

BASE_URL = "https://www.fuzu.com"
SITEMAP_INDEX_URL = BASE_URL + "/kenya/sitemap-job-listings.xml.gz"
JOB_URL_PREFIX = BASE_URL + "/kenya/jobs/"

_URL_BLOCK_RE = re.compile(r"<url>(.*?)</url>", re.S)
_LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>")
_LASTMOD_RE = re.compile(r"<lastmod>\s*(.*?)\s*</lastmod>")


def fetch_sitemap(session: PoliteSession, url: str) -> str:
    resp = session.get(url)
    if resp is None:
        return ""
    raw = resp.content
    try:
        raw = gzip.decompress(raw)
    except OSError:
        pass  # served already-decompressed
    return raw.decode("utf-8", "replace")


def category_sitemaps(session: PoliteSession, categories: list[str] | None) -> list[str]:
    urls = _LOC_RE.findall(fetch_sitemap(session, SITEMAP_INDEX_URL))
    if categories:
        urls = [u for u in urls if any(f"sitemap-{c}-listings" in u for c in categories)]
    return urls


def job_urls_from_sitemap(xml: str) -> list[tuple[str, str]]:
    """Return (url, lastmod) pairs for job detail pages in one category sitemap."""
    pairs = []
    for block in _URL_BLOCK_RE.findall(xml):
        loc = _LOC_RE.search(block)
        if loc and loc.group(1).startswith(JOB_URL_PREFIX):
            lastmod = _LASTMOD_RE.search(block)
            pairs.append((loc.group(1), lastmod.group(1) if lastmod else ""))
    return pairs


def parse_job_detail(session: PoliteSession, url: str) -> dict | None:
    resp = session.get(url)
    if resp is None:
        return None

    fields = parse_fuzu_page(resp.text)
    if not fields["is_job_page"]:
        logger.warning("No job description found at %s -- skipping.", url)
        return None

    email_domain = extract_email_domain(fields["description"], ignore_domains=("fuzu.com",))

    return {
        "source": "fuzu",
        "source_id": url.rstrip("/").split("/")[-1],
        "title": fields["title"],
        "location": fields["location"],
        "department": "",
        "salary_range": fields["salary_range"],
        "company_profile": fields["company_profile"],
        "description": fields["description"],
        "requirements": "",
        "benefits": "",
        "employment_type": fields["employment_type"],
        "required_experience": fields["required_experience"],
        "required_education": "",
        "industry": fields["industry"],
        "function": fields["function"],
        "telecommuting": "",
        "has_company_logo": "",
        "has_questions": "",
        "contact_email": "",
        "contact_email_domain": email_domain or "",
        "is_free_email_provider": int(is_free_email_provider(email_domain)),
        "posted_date": fields["posted_date"],
        "url": url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "fraudulent": "",
    }


def scrape(max_jobs: int, categories: list[str] | None, output_path: Path, delay: float) -> None:
    session = PoliteSession(delay_seconds=delay)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sitemaps = category_sitemaps(session, categories)
    logger.info("Found %d category sitemaps.", len(sitemaps))

    latest: dict[str, str] = {}
    for sm in sitemaps:
        pairs = job_urls_from_sitemap(fetch_sitemap(session, sm))
        logger.info("%s: %d job URLs", sm.rsplit("/", 1)[-1], len(pairs))
        for url, lastmod in pairs:
            latest[url] = max(lastmod, latest.get(url, ""))

    # Newest first (when the sitemap provides lastmod), so small runs get recent postings.
    all_links = sorted(latest, key=lambda u: (latest[u], u), reverse=True)[:max_jobs]
    logger.info("%d unique job URLs; scraping %d.", len(latest), len(all_links))

    written = 0
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=UNIFIED_COLUMNS)
        writer.writeheader()
        for i, url in enumerate(all_links, 1):
            record = parse_job_detail(session, url)
            if record:
                writer.writerow(record)
                written += 1
            if i % 10 == 0:
                logger.info("Scraped %d/%d job details", i, len(all_links))

    logger.info("Done. Wrote %d postings to %s", written, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Fuzu Kenya job postings via its job sitemaps.")
    parser.add_argument("--max-jobs", type=int, default=20,
                        help="Maximum number of job detail pages to fetch (3s apart by default).")
    parser.add_argument(
        "--categories", type=str, default="",
        help="Comma-separated sitemap category slugs, e.g. 'accounting-finance,sales'. Default: all.",
    )
    parser.add_argument("--output", type=str, default="../data/raw/fuzu_raw.csv")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between requests.")
    args = parser.parse_args()

    cats = [c.strip() for c in args.categories.split(",") if c.strip()] or None
    scrape(max_jobs=args.max_jobs, categories=cats, output_path=Path(args.output), delay=args.delay)
