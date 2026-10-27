"""Ekte Mat Online: Flask application factory."""

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_wtf.csrf import CSRFProtect

from .config import Config
from .models.image_generation import create_image_generator
from .models.repositories import Repositories


def create_app(config=None) -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(config or Config())

    app.extensions["repos"] = _build_repositories(app)
    app.extensions["image_generator"] = create_image_generator(app.config)
    CSRFProtect(app)

    from .controllers import auth

    auth.init_app(app)

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


def _build_image_store(app: Flask):
    if app.config["IMAGE_STORE"] == "memory":
        from .models.memory import MemoryImageStore

        return MemoryImageStore()
    from .models.images import LocalImageStore

    return LocalImageStore(app.config.get("IMAGE_FOLDER") or Path(app.instance_path) / "images")


def _build_repositories(app: Flask) -> Repositories:
    images = _build_image_store(app)
    backend = app.config["REPOSITORY_BACKEND"]
    if backend == "memory":
        from .models.memory import memory_repositories

        return memory_repositories(images)
    if backend == "neo4j":
        from .models.neo4j_db import create_driver
        from .models.neo4j_repos import neo4j_repositories

        driver = create_driver(
            app.config["NEO4J_URI"], app.config["NEO4J_USER"], app.config["NEO4J_PASSWORD"]
        )
        return neo4j_repositories(driver, images)
    raise ValueError(f"Unknown REPOSITORY_BACKEND: {backend}")
