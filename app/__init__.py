"""Ekte Mat Online: Flask application factory."""

from dotenv import load_dotenv
from flask import Flask

from .config import Config
from .models.repositories import Repositories


def create_app(config=None) -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(config or Config())

    app.extensions["repos"] = _build_repositories(app)

    from .controllers.account import bp as account_bp
    from .controllers.admin import bp as admin_bp
    from .controllers.shop import bp as shop_bp

    app.register_blueprint(shop_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)

    @app.template_filter("nok")
    def format_nok(amount: int) -> str:
        return f"kr\u00a0{amount:,}".replace(",", "\u00a0")  # non-breaking spaces

    return app


def _build_repositories(app: Flask) -> Repositories:
    backend = app.config["REPOSITORY_BACKEND"]
    if backend == "memory":
        from .models.memory import memory_repositories

        return memory_repositories()
    if backend == "neo4j":
        from .models.neo4j_db import create_driver
        from .models.neo4j_repos import neo4j_repositories

        driver = create_driver(
            app.config["NEO4J_URI"], app.config["NEO4J_USER"], app.config["NEO4J_PASSWORD"]
        )
        return neo4j_repositories(driver)
    raise ValueError(f"Unknown REPOSITORY_BACKEND: {backend}")
