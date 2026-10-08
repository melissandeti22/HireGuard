"""
FeatureExtractor: computes the stylometric feature vector described in
Section 3.2.2 of the proposal -- lexical, syntactic, punctuation/formatting,
and readability features -- from preprocessed job posting text, plus a small
set of content cues that operationalise the annotation-guide indicators
(payment/ID requests, unrealistic pay, urgency, messaging-app contact).

The same extractor is used by the API and by the Colab training notebook, so
any change here requires retraining the model.

Note on EMSCAD: the dataset masks contact details (#EMAIL_...#), so the free
email flag is always 0 for EMSCAD rows and the model learns that signal only
from the Kenyan scrapes.
"""

import math
import re
from dataclasses import dataclass, asdict

import textstat

from .preprocessor import Preprocessor

FREE_EMAIL_PROVIDERS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com",
    "aol.com", "icloud.com", "protonmail.com", "mail.com", "yandex.com",
    "gmx.com", "zoho.com",
}

URGENCY_TERMS = [
    "urgent", "urgently", "guaranteed", "guarantee", "immediate start",
    "no experience needed", "earn daily", "earn weekly", "easy money",
    "unlimited income", "act now", "limited slots",
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")

# Indicator 1 (annotation guide): requests for money or identity documents.
PAYMENT_OR_ID_RE = re.compile(
    r"\b(?:registration|processing|application|training|interview|medical|placement|booking)\s+fees?\b"
    r"|\bsend\s+(?:money|cash)\b|\bpay\s+(?:a\s+)?(?:ksh|kes|sh|\$)|\bm-?pesa\b|\bpaybill\b|\btill\s+(?:no|number)\b"
    r"|\bbank\s+(?:details|account\s+(?:details|number))\b|\bid\s+(?:card|number|no)\b|\bnational\s+id\b"
    r"|\bpassport\b|\bkra\s+pin\b|\bdate\s+of\s+birth\b",
    re.IGNORECASE,
)
# Indicator 3: amounts of money (salary claims).
MONEY_RE = re.compile(
    r"(?:\bksh?s?\.?|\bkes\b|\busd\b|\$|€|£)\s?\d[\d,.]*\s?k?\b|\b\d[\d,.]*\s?k?\s?(?:ksh|kes|usd|dollars|shillings|/=)",
    re.IGNORECASE,
)
SECOND_PERSON_RE = re.compile(r"\b(?:you|your|yours|yourself)\b", re.IGNORECASE)
MESSAGING_APP_RE = re.compile(r"\b(?:whats\s?app|telegram)\b", re.IGNORECASE)


@dataclass
class FeatureVector:
    ttr: float
    avg_sentence_length: float
    sentence_length_variance: float
    punctuation_density: float
    exclamation_density: float
    readability_score: float
    gunning_fog_index: float
    urgency_term_count: int
    free_email_flag: bool
    log_word_count: float
    caps_word_ratio: float
    money_mention_density: float
    payment_or_id_request_count: int
    second_person_density: float
    messaging_app_mention: int
    contact_email_domain: str | None

    def to_dict(self) -> dict:
        return asdict(self)


class FeatureExtractor:
    def __init__(self, preprocessor: Preprocessor | None = None):
        self.preprocessor = preprocessor or Preprocessor()

    def extract(self, raw_text: str) -> FeatureVector:
        cleaned = self.preprocessor.clean(raw_text)
        sentences = self.preprocessor.sentences(cleaned)
        tokens = self.preprocessor.words(cleaned)
        words = [w for w in tokens if any(ch.isalnum() for ch in w)]  # drop punctuation tokens
        syllables = [textstat.syllable_count(w) for w in words]

        return FeatureVector(
            ttr=self._type_token_ratio(words),
            avg_sentence_length=self._avg_sentence_length(sentences),
            sentence_length_variance=self._sentence_length_variance(sentences),
            punctuation_density=self._punctuation_density(cleaned),
            exclamation_density=self._char_density(cleaned, "!", words),
            readability_score=self._flesch_reading_ease(sentences, words, syllables),
            gunning_fog_index=self._gunning_fog(sentences, words, syllables),
            urgency_term_count=self._urgency_term_count(cleaned),
            free_email_flag=self._is_free_email(cleaned),
            log_word_count=math.log1p(len(words)),
            caps_word_ratio=self._caps_word_ratio(words),
            money_mention_density=self._per_100_words(len(MONEY_RE.findall(cleaned)), words),
            payment_or_id_request_count=len(PAYMENT_OR_ID_RE.findall(cleaned)),
            second_person_density=self._per_100_words(len(SECOND_PERSON_RE.findall(cleaned)), words),
            messaging_app_mention=int(bool(MESSAGING_APP_RE.search(cleaned))),
            contact_email_domain=self._email_domain(cleaned),
        )

    # -- lexical --
    def _type_token_ratio(self, words: list[str]) -> float:
        if not words:
            return 0.0
        return len(set(w.lower() for w in words)) / len(words)

    def _caps_word_ratio(self, words: list[str]) -> float:
        """Share of words of 3+ letters written entirely in capitals ("URGENT HIRING")."""
        long_words = [w for w in words if len(w) >= 3 and w.isalpha()]
        if not long_words:
            return 0.0
        return sum(w.isupper() for w in long_words) / len(long_words)

    # -- syntactic --
    def _sentence_lengths(self, sentences: list[str]) -> list[int]:
        return [len(s.split()) for s in sentences if s.split()]

    def _avg_sentence_length(self, sentences: list[str]) -> float:
        lengths = self._sentence_lengths(sentences)
        return sum(lengths) / len(lengths) if lengths else 0.0

    def _sentence_length_variance(self, sentences: list[str]) -> float:
        lengths = self._sentence_lengths(sentences)
        if len(lengths) < 2:
            return 0.0
        mean = sum(lengths) / len(lengths)
        return sum((l - mean) ** 2 for l in lengths) / len(lengths)

    # -- punctuation / formatting --
    def _punctuation_density(self, text: str) -> float:
        if not text:
            return 0.0
        punct_count = sum(1 for ch in text if ch in '.,!?;:"\'-()')
        return punct_count / len(text)

    def _char_density(self, text: str, char: str, words: list[str]) -> float:
        return text.count(char) / max(len(words), 1)

    def _per_100_words(self, count: int, words: list[str]) -> float:
        return 100 * count / max(len(words), 1)

    def _urgency_term_count(self, text: str) -> int:
        lowered = text.lower()
        return sum(lowered.count(term) for term in URGENCY_TERMS)

    # -- readability (syllables from textstat; sentences from the preprocessor) --
    def _flesch_reading_ease(self, sentences, words, syllables) -> float:
        if not sentences or not words:
            return 0.0
        return 206.835 - 1.015 * (len(words) / len(sentences)) - 84.6 * (sum(syllables) / len(words))

    def _gunning_fog(self, sentences, words, syllables) -> float:
        if not sentences or not words:
            return 0.0
        complex_words = sum(1 for s in syllables if s >= 3)
        return 0.4 * ((len(words) / len(sentences)) + 100 * (complex_words / len(words)))

    # -- metadata --
    def _email_domain(self, text: str) -> str | None:
        match = EMAIL_RE.search(text)
        return match.group(1).lower() if match else None

    def _is_free_email(self, text: str) -> bool:
        domain = self._email_domain(text)
        return domain in FREE_EMAIL_PROVIDERS if domain else False
