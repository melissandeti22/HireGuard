"""
One-time setup script: creates all five tables from the SQLAlchemy models
in app/db/models.py, and seeds the placeholder "demo-user" account that
the frontend uses until real login is built.

Works with both SQLite (default, no setup needed) and PostgreSQL
(set DATABASE_URL in .env first).

Usage:
    python init_db.py
"""

import os

from app import create_app
from app.config import DEFAULT_SQLITE_PATH
from app.db.database import db
from app.db.models import User

os.makedirs(os.path.dirname(DEFAULT_SQLITE_PATH), exist_ok=True)

app = create_app()

with app.app_context():
    db.create_all()
    print("Tables created: users, job_postings, feature_vectors, "
          "classification_results, explainability_reports")

    if not db.session.get(User, "demo-user"):
        db.session.add(User(
            user_id="demo-user",
            email="demo@hireguard.local",
            password_hash="not-a-real-password",
        ))
        db.session.commit()
        print("Seeded placeholder user: demo-user")
    else:
        print("demo-user already exists, skipping seed")

    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
