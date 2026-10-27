"""Model layer: domain classes and repositories. The only layer that touches storage."""

from flask import current_app

from .repositories import Repositories


def repos() -> Repositories:
    """The repositories configured for the running app (Neo4j, or in-memory in tests)."""
    return current_app.extensions["repos"]
