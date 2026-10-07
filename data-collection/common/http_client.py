"""
Polite HTTP client for scraping BrighterMonday Kenya and Fuzu Kenya.

Design choices, matching the proposal's stated tools (Section 3.8.2 --
BeautifulSoup and Requests) and its data privacy commitments (Section
3.2.1: "no personally identifiable information will be retained from
scraped postings beyond the text fields required for stylometric
analysis"):

- Checks robots.txt before crawling any path, and refuses to fetch
  disallowed paths.
- Rate-limits every request (default 3s) so the scraper behaves like a
  single slow human browsing, not a bot hammering the site.
- Retries transient failures (5xx, timeouts) with exponential backoff,
  but does NOT retry 4xx (those are treated as "this page doesn't exist
  / isn't allowed").
- Never touches anything except the publicly viewable job listing pages.
"""

import time
import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter, Retry

from .config import REQUEST_HEADERS, REQUEST_TIMEOUT_SECONDS, REQUEST_DELAY_SECONDS, MAX_RETRIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("http_client")


class PoliteSession:
    """A requests.Session wrapper that rate-limits and respects robots.txt."""

    def __init__(self, delay_seconds: float = REQUEST_DELAY_SECONDS):
        self.delay_seconds = delay_seconds
        self._last_request_time = 0.0
        self._robots_cache: dict[str, RobotFileParser] = {}

        self.session = requests.Session()
        self.session.headers.update(REQUEST_HEADERS)
        retries = Retry(
            total=MAX_RETRIES,
            backoff_factor=2,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _robots_allows(self, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots_cache:
            rp = RobotFileParser()
            robots_url = f"{origin}/robots.txt"
            rp.set_url(robots_url)
            # NOTE: deliberately NOT using rp.read() here. RobotFileParser.read()
            # fetches robots.txt with urllib's own opener, which sends the
            # generic "Python-urllib/x.y" User-Agent. Sites behind Cloudflare
            # or similar WAFs (BrighterMonday included -- note the /cdn-cgi/
            # rule in their robots.txt) often 403 that generic UA outright.
            # When urllib.robotparser hits a 401/403 it fails CLOSED (blocks
            # everything), even if the actual rules would have allowed the
            # path. Fetching with our own session + descriptive UA avoids
            # that false block.
            try:
                resp = self.session.get(robots_url, timeout=REQUEST_TIMEOUT_SECONDS)
            except requests.RequestException as e:
                logger.warning("Could not fetch robots.txt for %s (%s); refusing to scrape.", origin, e)
                self._robots_cache[origin] = None
                return False

            if resp is None or resp.status_code >= 400:
                status = resp.status_code if resp is not None else "no response"
                logger.warning(
                    "robots.txt fetch for %s returned %s; refusing to scrape.", origin, status
                )
                self._robots_cache[origin] = None
                return False

            try:
                rp.parse(resp.text.splitlines())
            except Exception as e:
                logger.warning("Could not parse robots.txt for %s (%s); refusing to scrape.", origin, e)
                self._robots_cache[origin] = None
                return False

            self._robots_cache[origin] = rp

        rp = self._robots_cache[origin]
        if rp is None:
            return False
        return rp.can_fetch(REQUEST_HEADERS["User-Agent"], url)

    def get(self, url: str, **kwargs) -> requests.Response | None:
        if not self._robots_allows(url):
            logger.warning("robots.txt disallows fetching %s -- skipping.", url)
            return None

        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)

        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)
            self._last_request_time = time.monotonic()
        except requests.RequestException as e:
            logger.error("Request failed for %s: %s", url, e)
            return None

        if resp.status_code == 200:
            return resp

        logger.warning("Non-200 response (%s) for %s", resp.status_code, url)
        return None
