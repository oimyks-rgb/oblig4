"""User accounts: login and customer registration."""

import re
import uuid
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from .domain import Role, User
from .repositories import UserRepository

PASSWORD_MIN = 10
NAME_MAX = 100
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def authenticate(users: UserRepository, email: str, password: str) -> Optional[User]:
    """The user with this e-mail and password, or None. Never says which one was wrong."""
    user = users.get_by_email(email or "")
    if user and check_password_hash(user.password_hash, password or ""):
        return user
    return None


def register_customer(
    users: UserRepository, name: str, email: str, password: str, confirm: str
) -> tuple[Optional[User], dict[str, str]]:
    """Create a customer account. Returns (user, {}) or (None, field errors)."""
    errors = {}
    name, email = (name or "").strip(), (email or "").strip().lower()
    if not name:
        errors["name"] = "Enter your name."
    elif len(name) > NAME_MAX:
        errors["name"] = f"Name can be at most {NAME_MAX} characters."
    if not _EMAIL.match(email):
        errors["email"] = "Enter a valid e-mail address."
    elif users.get_by_email(email):
        errors["email"] = "This e-mail address already has an account. Log in instead."
    if len(password or "") < PASSWORD_MIN:
        errors["password"] = f"Use at least {PASSWORD_MIN} characters."
    elif password != confirm:
        errors["confirm"] = "The passwords do not match."
    if errors:
        return None, errors
    user = users.add(User(uuid.uuid4().hex, email, name, generate_password_hash(password), Role.CUSTOMER))
    return user, {}
