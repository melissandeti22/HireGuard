"""
Text cleaning and metadata-extraction helpers shared by all scrapers and
the EMSCAD loader. Keeps HTML cleaning consistent so stylometric features
computed later (Section 3.2.2) aren't skewed by leftover markup.
"""

import re
import unicodedata
from bs4 import BeautifulSoup

from .config import FREE_EMAIL_PROVIDERS

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")

# Common Cyrillic homoglyphs -> Latin equivalents. Referenced in Section
# 2.2.2 / 2.3.2 of the proposal as an evasion technique that must be
# normalized before feature extraction.
CYRILLIC_TO_LATIN = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y",
    "х": "x", "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M",
    "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "У": "Y", "Х": "X",
}


def normalize_homoglyphs(text: str) -> str:
    """Convert visually-identical Cyrillic characters to Latin equivalents."""
    if not text:
        return text
    text = unicodedata.normalize("NFKC", text)
    return "".join(CYRILLIC_TO_LATIN.get(ch, ch) for ch in text)


def clean_html(raw_html: str) -> str:
    """Strip HTML tags, collapse whitespace, normalize homoglyphs.

    Explicitly removes <script> and <style> tags first -- BeautifulSoup's
    get_text() includes their raw contents by default (JS code, CSS rules),
    which otherwise leaks into the "clean" text and corrupts stylometric
    features downstream.
    """
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = normalize_homoglyphs(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_email_domain(text: str) -> str | None:
    """Return the first email domain found in text, or None."""
    if not text:
        return None
    match = EMAIL_RE.search(normalize_homoglyphs(text))
    return match.group(1).lower() if match else None


def is_free_email_provider(domain: str | None) -> bool:
    if not domain:
        return False
    return domain.lower() in FREE_EMAIL_PROVIDERS
