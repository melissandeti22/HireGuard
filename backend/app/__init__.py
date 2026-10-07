"""
HireGuard Flask application factory.

Wires together the four backend pieces from the system design (Chapter 4):
the Application Tier (this Flask app), the Machine Learning Tier
(app/ml/*), and the Data Tier (app/db/*, PostgreSQL). The Presentation
Tier is the separate React app in /frontend.
"""

from flask import Flask
from flask_cors import CORS

from .config import Config
from .db.database import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    CORS(app)  # allows the React dev server (different origin) to call this API

    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "hireguard-api"}

    return app
