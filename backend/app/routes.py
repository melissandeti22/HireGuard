"""
API routes for HireGuard, implementing the primary use case from the
Sequence Diagram (Figure 4.5): a job seeker submits posting text and
receives a classification plus SHAP explanation, with everything
persisted to PostgreSQL.
"""

from flask import Blueprint, current_app, jsonify, request

from .db.database import db
from .db.models import (
    ClassificationResult as ClassificationResultModel,
    ExplainabilityReport as ExplainabilityReportModel,
    FeatureVector as FeatureVectorModel,
    JobPosting,
)
from .ml.classifier import Classifier
from .ml.feature_extractor import FeatureExtractor
from .ml.preprocessor import Preprocessor
from .ml.shap_explainer import SHAPExplainer

api_bp = Blueprint("api", __name__)

_preprocessor = Preprocessor()
_feature_extractor = FeatureExtractor(_preprocessor)


def _get_classifier() -> Classifier:
    return Classifier(current_app.config["MODEL_PATH"])


def _get_explainer() -> SHAPExplainer:
    return SHAPExplainer(current_app.config["EXPLAINER_PATH"])


@api_bp.post("/classify")
def classify():
    """
    Request body: {"text": "...", "source_platform": "BrighterMonday", "user_id": "..."}
    This matches the Activity Diagram's validation-then-pipeline flow (Figure 4.2):
    empty input is rejected before the classification pipeline runs.
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    source_platform = data.get("source_platform", "")
    user_id = data.get("user_id")

    if not text:
        return jsonify({"error": "Job posting text is required."}), 400
    if not user_id:
        return jsonify({"error": "user_id is required."}), 400

    # Pipeline: Preprocessor -> FeatureExtractor -> Classifier -> SHAPExplainer
    vector = _feature_extractor.extract(text)
    result = _get_classifier().predict(vector)

    report = None
    if result.label == "fraudulent":
        report = _get_explainer().explain(vector, result)

    # Persist: JobPosting -> FeatureVector -> ClassificationResult -> ExplainabilityReport
    posting = JobPosting(raw_text=text, source_platform=source_platform, user_id=user_id)
    db.session.add(posting)
    db.session.flush()  # get posting_id before the dependent rows

    vector_row = FeatureVectorModel(
        ttr=vector.ttr,
        avg_sentence_length=vector.avg_sentence_length,
        sentence_length_variance=vector.sentence_length_variance,
        punctuation_density=vector.punctuation_density,
        exclamation_density=vector.exclamation_density,
        readability_score=vector.readability_score,
        gunning_fog_index=vector.gunning_fog_index,
        free_email_flag=vector.free_email_flag,
        posting_id=posting.posting_id,
    )
    db.session.add(vector_row)
    db.session.flush()

    result_row = ClassificationResultModel(
        label=result.label,
        confidence_score=result.confidence_score,
        vector_id=vector_row.vector_id,
    )
    db.session.add(result_row)
    db.session.flush()

    report_payload = None
    if report:
        report_row = ExplainabilityReportModel(
            top_features=report.top_features,
            shap_values=[f.get("shap_value") for f in report.top_features],
            plain_language_summary=report.plain_language_summary,
            result_id=result_row.result_id,
        )
        db.session.add(report_row)
        report_payload = {
            "top_features": report.top_features,
            "summary": report.plain_language_summary,
        }

    db.session.commit()

    return jsonify({
        "posting_id": posting.posting_id,
        "label": result.label,
        "confidence_score": result.confidence_score,
        "explainability_report": report_payload,
        "is_stub_model": getattr(result, "is_stub", False),
    })


@api_bp.get("/history")
def history():
    """Returns paginated submission history, matching the wireframe (Figure 4.9)."""
    user_id = request.args.get("user_id")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    query = JobPosting.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    query = query.order_by(JobPosting.submitted_at.desc())

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    items = []
    for posting in paginated.items:
        result = None
        if posting.feature_vector and posting.feature_vector.classification_result:
            result = posting.feature_vector.classification_result
        items.append({
            "posting_id": posting.posting_id,
            "title_snippet": posting.raw_text[:60],
            "source_platform": posting.source_platform,
            "submitted_at": posting.submitted_at.isoformat(),
            "label": result.label if result else None,
        })

    return jsonify({
        "items": items,
        "page": page,
        "total_pages": paginated.pages,
        "total_items": paginated.total,
    })
