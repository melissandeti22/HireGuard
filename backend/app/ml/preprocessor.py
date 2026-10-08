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

# EMSCAD replaces contact details with hashed tokens such as
# "#EMAIL_9f3a...#"; the hash would otherwise count as a long, unique word.
_EMSCAD_MASK_RE = re.compile(r"#(EMAIL|URL|PHONE)_[0-9a-f]+#")

# Sentence boundaries that carry no full stop: bullets, and paragraphs or
# list items glued together when HTML was stripped ("...InstituteOur passion").
_BULLET_RE = re.compile(r"\s*[•·●▪◦➢►✓✔]\s*")
_GLUED_RE = re.compile(r"(?<=[a-z0-9)\]:])(?=[A-Z][a-z])")

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
        """Strip HTML tags/scripts, replace dataset mask tokens, normalize
        homoglyphs, and collapse whitespace while keeping line breaks
        (they mark sentence boundaries in bulleted postings)."""
        if not raw_text:
            return ""
        soup = BeautifulSoup(raw_text, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
        text = _EMSCAD_MASK_RE.sub(lambda m: f" [{m.group(1).lower()}] ", text)
        text = self.normalize_homoglyphs(text)
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        return re.sub(r"\s*\n\s*", "\n", text).strip()

    def segment(self, cleaned_text: str) -> str:
        """Put each bullet, glued paragraph and line on its own line."""
        text = _BULLET_RE.sub("\n", cleaned_text)
        return _GLUED_RE.sub("\n", text)

    def sentences(self, cleaned_text: str) -> list[str]:
        lines = self.segment(cleaned_text).split("\n")
        return [s for line in lines if line.strip() for s in nltk.sent_tokenize(line)]

    def words(self, cleaned_text: str) -> list[str]:
        return nltk.word_tokenize(self.segment(cleaned_text).replace("\n", " "))
