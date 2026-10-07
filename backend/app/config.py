"""
App configuration, loaded from environment variables (see .env.example).
Using python-dotenv so a local .env file works without extra setup.

If DATABASE_URL is not set, the app falls back to a local SQLite file
(backend/instance/hireguard.db) so you can run everything without
installing PostgreSQL first. Set DATABASE_URL in .env to switch to
PostgreSQL -- no code changes needed.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "instance", "hireguard.db")


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or f"sqlite:///{DEFAULT_SQLITE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Path to the serialized Random Forest model + fitted SHAP TreeExplainer
    # (Section 3.7.1 of the proposal). Until these exist, the API runs in stub mode.
    MODEL_PATH = os.environ.get("MODEL_PATH", os.path.join(BASE_DIR, "app/ml/artifacts/random_forest_model.joblib"))
    EXPLAINER_PATH = os.environ.get("EXPLAINER_PATH", os.path.join(BASE_DIR, "app/ml/artifacts/shap_explainer.joblib"))

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
