import os

from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

    from app.routes import complete_match, complete_match_mongo, main

    app.register_blueprint(main.bp)
    app.register_blueprint(complete_match.bp)
    app.register_blueprint(complete_match_mongo.bp)
    return app
