"""
FeatureExtractor: computes the stylometric feature vector described in
Section 3.2.2 of the proposal -- lexical, syntactic, punctuation/formatting,
and readability features -- from preprocessed job posting text.

Each feature here is implemented directly against the definition in the
proposal. Swap in textstat for Flesch-Kincaid / Gunning Fog once that
dependency is installed (see backend/requirements.txt) -- stub formulas
are provided below so this module runs standalone in the meantime.
"""

import re
from dataclasses import dataclass, asdict

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
    contact_email_domain: str | None

    def to_dict(self) -> dict:
        return asdict(self)


class FeatureExtractor:
    def __init__(self, preprocessor: Preprocessor | None = None):
        self.preprocessor = preprocessor or Preprocessor()

    def extract(self, raw_text: str) -> FeatureVector:
        cleaned = self.preprocessor.clean(raw_text)
        sentences = self.preprocessor.sentences(cleaned)
        words = self.preprocessor.words(cleaned)

        return FeatureVector(
            ttr=self._type_token_ratio(words),
            avg_sentence_length=self._avg_sentence_length(sentences),
            sentence_length_variance=self._sentence_length_variance(sentences),
            punctuation_density=self._punctuation_density(cleaned),
            exclamation_density=self._char_density(cleaned, "!"),
            readability_score=self._flesch_kincaid_stub(cleaned, sentences, words),
            gunning_fog_index=self._gunning_fog_stub(sentences, words),
            urgency_term_count=self._urgency_term_count(cleaned),
            free_email_flag=self._is_free_email(cleaned),
            contact_email_domain=self._email_domain(cleaned),
        )

    # -- lexical --
    def _type_token_ratio(self, words: list[str]) -> float:
        if not words:
            return 0.0
        return len(set(w.lower() for w in words)) / len(words)

    # -- syntactic --
    def _avg_sentence_length(self, sentences: list[str]) -> float:
        if not sentences:
            return 0.0
        lengths = [len(s.split()) for s in sentences]
        return sum(lengths) / len(lengths)

    def _sentence_length_variance(self, sentences: list[str]) -> float:
        if len(sentences) < 2:
            return 0.0
        lengths = [len(s.split()) for s in sentences]
        mean = sum(lengths) / len(lengths)
        return sum((l - mean) ** 2 for l in lengths) / len(lengths)

    # -- punctuation / formatting --
    def _punctuation_density(self, text: str) -> float:
        if not text:
            return 0.0
        punct_count = sum(1 for ch in text if ch in '.,!?;:"\'-()')
        return punct_count / len(text)

    def _char_density(self, text: str, char: str) -> float:
        if not text:
            return 0.0
        return text.count(char) / max(len(text.split()), 1)

    def _urgency_term_count(self, text: str) -> int:
        lowered = text.lower()
        return sum(lowered.count(term) for term in URGENCY_TERMS)

    # -- readability (stub formulas -- replace with textstat once installed) --
    def _flesch_kincaid_stub(self, text, sentences, words) -> float:
        if not sentences or not words:
            return 0.0
        syllables = sum(self._estimate_syllables(w) for w in words)
        return (
            206.835
            - 1.015 * (len(words) / len(sentences))
            - 84.6 * (syllables / len(words))
        )

    def _gunning_fog_stub(self, sentences, words) -> float:
        if not sentences or not words:
            return 0.0
        complex_words = sum(1 for w in words if self._estimate_syllables(w) >= 3)
        return 0.4 * (
            (len(words) / len(sentences)) + 100 * (complex_words / len(words))
        )

    def _estimate_syllables(self, word: str) -> int:
        word = word.lower()
        count = len(re.findall(r"[aeiouy]+", word))
        return max(count, 1)

    # -- metadata --
    def _email_domain(self, text: str) -> str | None:
        match = EMAIL_RE.search(text)
        return match.group(1).lower() if match else None

    def _is_free_email(self, text: str) -> bool:
        domain = self._email_domain(text)
        return domain in FREE_EMAIL_PROVIDERS if domain else False
