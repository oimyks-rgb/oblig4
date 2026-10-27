"""User accounts: password checks. Used by the login controller."""

from typing import Optional

from werkzeug.security import check_password_hash

from .domain import User
from .repositories import UserRepository


def authenticate(users: UserRepository, email: str, password: str) -> Optional[User]:
    """The user with this e-mail and password, or None. Never says which one was wrong."""
    user = users.get_by_email(email or "")
    if user and check_password_hash(user.password_hash, password or ""):
        return user
    return None
