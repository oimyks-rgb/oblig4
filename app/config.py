"""Configuration. Values come from environment variables (loaded from .env)."""

import os
import secrets


class Config:
    REPOSITORY_BACKEND = "neo4j"
    TESTING = False
    SESSION_COOKIE_SAMESITE = "Lax"

    def __init__(self):
        # Read at instantiation, after create_app() has loaded .env
        self.SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
        self.NEO4J_URI = os.environ.get("NEO4J_URI", "")
        self.NEO4J_USER = os.environ.get("NEO4J_USER", "")
        self.NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")


class TestConfig(Config):
    """In-memory repositories; never touches Neo4j."""

    __test__ = False  # not a pytest test class

    REPOSITORY_BACKEND = "memory"
    TESTING = True
    WTF_CSRF_ENABLED = False

    def __init__(self):
        super().__init__()
        self.SECRET_KEY = "test"
