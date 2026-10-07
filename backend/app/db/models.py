"""
SQLAlchemy models for HireGuard's five core tables, matching the Entity
Relationship Diagram and Database Schema (Figures 4.3 / 4.6):

    users (1) --< job_postings (1) -- (1) feature_vectors
                                           (1) -- (1) classification_results
                                                       (1) -- (1) explainability_reports
"""

import uuid
from datetime import datetime, timezone

from .database import db


def _uuid():
    return str(uuid.uuid4())


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.String(36), primary_key=True, default=_uuid)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    registered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    postings = db.relationship("JobPosting", backref="user", lazy=True)


class JobPosting(db.Model):
    __tablename__ = "job_postings"

    posting_id = db.Column(db.String(36), primary_key=True, default=_uuid)
    raw_text = db.Column(db.Text, nullable=False)
    source_platform = db.Column(db.String(100))
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.String(36), db.ForeignKey("users.user_id"), nullable=False)

    feature_vector = db.relationship(
        "FeatureVector", backref="posting", uselist=False, lazy=True
    )


class FeatureVector(db.Model):
    __tablename__ = "feature_vectors"

    vector_id = db.Column(db.String(36), primary_key=True, default=_uuid)
    ttr = db.Column(db.Float)
    avg_sentence_length = db.Column(db.Float)
    sentence_length_variance = db.Column(db.Float)
    punctuation_density = db.Column(db.Float)
    exclamation_density = db.Column(db.Float)
    readability_score = db.Column(db.Float)
    gunning_fog_index = db.Column(db.Float)
    free_email_flag = db.Column(db.Boolean, default=False)
    posting_id = db.Column(
        db.String(36), db.ForeignKey("job_postings.posting_id"), nullable=False, unique=True
    )

    classification_result = db.relationship(
        "ClassificationResult", backref="feature_vector", uselist=False, lazy=True
    )


class ClassificationResult(db.Model):
    __tablename__ = "classification_results"

    result_id = db.Column(db.String(36), primary_key=True, default=_uuid)
    label = db.Column(db.String(20), nullable=False)  # "fraudulent" | "legitimate"
    confidence_score = db.Column(db.Float, nullable=False)
    classified_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    vector_id = db.Column(
        db.String(36), db.ForeignKey("feature_vectors.vector_id"), nullable=False, unique=True
    )

    explainability_report = db.relationship(
        "ExplainabilityReport", backref="classification_result", uselist=False, lazy=True
    )


class ExplainabilityReport(db.Model):
    __tablename__ = "explainability_reports"

    report_id = db.Column(db.String(36), primary_key=True, default=_uuid)
    top_features = db.Column(db.JSON)
    shap_values = db.Column(db.JSON)
    plain_language_summary = db.Column(db.Text)
    result_id = db.Column(
        db.String(36), db.ForeignKey("classification_results.result_id"),
        nullable=False, unique=True,
    )
