"""Model layer: domain classes and repositories. The only layer that touches storage."""

from flask import current_app

from .image_generation import ImageGenerator
from .repositories import Repositories


def repos() -> Repositories:
    """The repositories configured for the running app (Neo4j, or in-memory in tests)."""
    return current_app.extensions["repos"]


def image_generator() -> "ImageGenerator | None":
    """The configured AI image service, or None when IMAGE_GENERATOR is not set."""
    return current_app.extensions.get("image_generator")
