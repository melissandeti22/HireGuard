"""
Preprocessor: a stateless utility that cleans, tokenizes, and normalizes
raw job posting text before feature extraction (Section 3.2.2 of the
proposal). Reuses the HTML-cleaning and Cyrillic homoglyph normalization
already built and tested in data-collection/common/text_utils.py.
"""

import re
import unicodedata

import nltk
from bs4 import BeautifulSoup

# NLTK's sentence/word tokenizer models -- downloaded once, cached locally.
for pkg in ("punkt", "punkt_tab"):
    try:
        nltk.data.find(f"tokenizers/{pkg}")
    except LookupError:
        nltk.download(pkg, quiet=True)

CYRILLIC_TO_LATIN = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y",
    "х": "x", "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M",
    "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "У": "Y", "Х": "X",
}


class Preprocessor:
    """Cleans and tokenizes raw posting text. Stateless -- safe to reuse
    a single instance across requests."""

    def normalize_homoglyphs(self, text: str) -> str:
        if not text:
            return text
        text = unicodedata.normalize("NFKC", text)
        return "".join(CYRILLIC_TO_LATIN.get(ch, ch) for ch in text)

    def clean(self, raw_text: str) -> str:
        """Strip HTML tags/scripts, collapse whitespace, normalize homoglyphs."""
        if not raw_text:
            return ""
        soup = BeautifulSoup(raw_text, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
        text = self.normalize_homoglyphs(text)
        return re.sub(r"\s+", " ", text).strip()

    def sentences(self, cleaned_text: str) -> list[str]:
        return nltk.sent_tokenize(cleaned_text)

    def words(self, cleaned_text: str) -> list[str]:
        return nltk.word_tokenize(cleaned_text)
