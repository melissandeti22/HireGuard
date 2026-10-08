"""
Classifier: wraps the trained Random Forest model (Section 3.2.3) and
produces a binary fraud classification with a confidence score.

NOTE: no trained model exists yet -- that comes out of the Colab
training notebook, once the combined EMSCAD + BrighterMonday + Fuzu
dataset is labeled and ready (Section 3.2.1-3.2.3). Until
app/ml/artifacts/random_forest_model.joblib exists, this class runs in
"stub mode" and returns a clearly-labeled placeholder result rather than
crashing the API, so the rest of the pipeline (routes, DB persistence,
frontend) can be built and tested end-to-end before training finishes.
"""

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

from .feature_extractor import FeatureVector

FEATURE_ORDER = [
    "ttr", "avg_sentence_length", "sentence_length_variance",
    "punctuation_density", "exclamation_density", "readability_score",
    "gunning_fog_index", "urgency_term_count", "free_email_flag",
    "log_word_count", "caps_word_ratio", "money_mention_density",
    "payment_or_id_request_count", "second_person_density", "messaging_app_mention",
]


@dataclass
class ClassificationResult:
    label: str  # "fraudulent" | "legitimate"
    confidence_score: float
    is_stub: bool = False


class Classifier:
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.model = None
        if self.model_path.exists():
            self.model = joblib.load(self.model_path)

    def vector_to_array(self, vector: FeatureVector) -> np.ndarray:
        d = vector.to_dict()
        return np.array([[float(d[f]) for f in FEATURE_ORDER]])

    def predict(self, vector: FeatureVector) -> ClassificationResult:
        if self.model is None:
            # Stub mode: no trained model on disk yet. Flag free-email +
            # high urgency-term count as a crude placeholder so the rest
            # of the pipeline has something real to persist and display.
            red_flags = int(vector.free_email_flag) + (1 if vector.urgency_term_count > 0 else 0)
            label = "fraudulent" if red_flags >= 2 else "legitimate"
            return ClassificationResult(label=label, confidence_score=0.5, is_stub=True)

        X = self.vector_to_array(vector)
        proba = self.model.predict_proba(X)[0]
        pred = self.model.predict(X)[0]
        label = "fraudulent" if pred == 1 else "legitimate"
        confidence = float(max(proba))
        return ClassificationResult(label=label, confidence_score=confidence)
