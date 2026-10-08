"""
SHAPExplainer: wraps a fitted SHAP TreeExplainer over the trained Random
Forest to produce the feature-level, plain-language explainability report
described in Section 2.6 and 3.2.3 of the proposal.

Like Classifier, this runs in stub mode until a fitted explainer exists
on disk (produced alongside the trained model in the Colab notebook).
"""

from dataclasses import dataclass
from pathlib import Path

import joblib

from .classifier import FEATURE_ORDER
from .feature_extractor import FeatureVector

# Plain-language labels for each feature, used to build the
# human-readable summary regardless of stub/real mode.
FEATURE_DESCRIPTIONS = {
    "ttr": "low vocabulary richness (repetitive wording)",
    "avg_sentence_length": "unusually short or long sentences",
    "sentence_length_variance": "inconsistent sentence structure",
    "punctuation_density": "high punctuation density",
    "exclamation_density": "excessive exclamation marks",
    "readability_score": "unusual readability level",
    "gunning_fog_index": "unusual text complexity",
    "urgency_term_count": "urgency / over-promising language",
    "free_email_flag": "use of a free email provider instead of a corporate domain",
    "log_word_count": "unusually short or long posting",
    "caps_word_ratio": "heavy use of capital letters",
    "money_mention_density": "frequent mentions of money or pay",
    "payment_or_id_request_count": "requests for payment, M-Pesa, ID or bank details",
    "second_person_density": "heavy direct 'you' address to the reader",
    "messaging_app_mention": "contact through WhatsApp or Telegram",
}


@dataclass
class ExplainabilityReport:
    top_features: list[dict]  # [{"feature": str, "impact": "high"|"moderate", "shap_value": float}]
    plain_language_summary: str
    is_stub: bool = False


class SHAPExplainer:
    def __init__(self, explainer_path: str, classifier_model=None):
        self.explainer_path = Path(explainer_path)
        self.explainer = None
        if self.explainer_path.exists():
            self.explainer = joblib.load(self.explainer_path)

    def explain(self, vector: FeatureVector, result) -> ExplainabilityReport:
        if self.explainer is None:
            return self._stub_explanation(vector, result)

        X = self._vector_to_array(vector)
        contributions = self._fraud_class_contributions(self.explainer.shap_values(X))

        ranked = sorted(
            zip(FEATURE_ORDER, contributions), key=lambda p: abs(p[1]), reverse=True
        )[:3]
        top_features = [
            {
                "feature": name,
                "description": FEATURE_DESCRIPTIONS.get(name, name),
                "shap_value": float(value),
                "impact": "high" if abs(value) > 0.1 else "moderate",
            }
            for name, value in ranked
        ]
        summary = self._build_summary(top_features, result.label)
        return ExplainabilityReport(top_features=top_features, plain_language_summary=summary)

    @staticmethod
    def _fraud_class_contributions(shap_values):
        """Per-feature SHAP values for the fraudulent class (1) of the single row explained.

        shap < 0.45 returns a list [class_0, class_1] of (rows, features) arrays;
        shap >= 0.45 returns one (rows, features, classes) array for classifiers.
        """
        import numpy as np
        if isinstance(shap_values, list):
            return shap_values[1][0]
        values = np.asarray(shap_values)
        return values[0, :, 1] if values.ndim == 3 else values[0]

    def _stub_explanation(self, vector: FeatureVector, result) -> ExplainabilityReport:
        """Heuristic explanation used until a fitted SHAP explainer exists."""
        candidates = []
        if vector.free_email_flag:
            candidates.append(("free_email_flag", "high"))
        if vector.urgency_term_count > 0:
            candidates.append(("urgency_term_count", "moderate"))
        if vector.ttr < 0.4:
            candidates.append(("ttr", "moderate"))
        if not candidates:
            candidates.append(("ttr", "moderate"))

        top_features = [
            {
                "feature": name,
                "description": FEATURE_DESCRIPTIONS.get(name, name),
                "shap_value": None,
                "impact": impact,
            }
            for name, impact in candidates[:3]
        ]
        summary = self._build_summary(top_features, result.label)
        return ExplainabilityReport(
            top_features=top_features, plain_language_summary=summary, is_stub=True
        )

    def _build_summary(self, top_features: list[dict], label: str) -> str:
        reasons = "; ".join(f["description"] for f in top_features)
        if label == "fraudulent":
            return f"Flagged as likely fraudulent due to: {reasons}."
        return f"Classified as legitimate. Noted characteristics: {reasons}."

    def _vector_to_array(self, vector: FeatureVector):
        import numpy as np
        d = vector.to_dict()
        return np.array([[float(d[f]) for f in FEATURE_ORDER]])
