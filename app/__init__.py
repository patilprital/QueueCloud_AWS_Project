import os
from flask import Flask
from app.config import Config
from app.extensions import db
from app.routes.auth import auth_bp
from app.routes.patient import patient_bp
from app.routes.admin import admin_bp
from app.aws_services import get_static_url


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "0") == "1",
    )

    db.init_app(app)

    # Register s3_url() as a Jinja2 global so every template can use it:
    #   <link href="{{ s3_url('static/css/style.css') }}">
    # When S3 is not configured it falls back to /static/css/style.css
    app.jinja_env.globals["s3_url"] = get_static_url

    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp, url_prefix="/patient")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app


app = create_app()
