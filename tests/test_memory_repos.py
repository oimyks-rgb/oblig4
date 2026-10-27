"""Repository contract tests, run against the in-memory backend.

test_neo4j_repos.py runs the same checks against Neo4j.
"""

import pytest

from app.models.domain import Allergen, EventCategory, Role, User
from app.models.memory import MemoryFoodItemRepository, MemoryUserRepository
from tests.conftest import make_item


def check_food_item_repository(repo, prefix=""):
    a = make_item(prefix + "a", prefix + "Apple cake", event_categories=[EventCategory.BIRTHDAY])
    b = make_item(prefix + "b", prefix + "Beef stew", published=False)
    repo.add(a)
    repo.add(b)

    assert repo.get(a.id) == a
    assert repo.get(prefix + "missing") is None
    with pytest.raises(ValueError):
        repo.add(a)

    ids = lambda items: {i.id for i in items}
    assert {a.id, b.id} <= ids(repo.list())
    assert a.id in ids(repo.list(published_only=True))
    assert b.id not in ids(repo.list(published_only=True))
    assert a.id in ids(repo.list(category=EventCategory.BIRTHDAY))
    assert b.id not in ids(repo.list(category=EventCategory.BIRTHDAY))

    a.price_nok = 200
    a.allergens = []
    a.no_allergens = True
    a.event_categories = [EventCategory.WEDDING]
    repo.update(a)
    assert repo.get(a.id) == a
    assert a.id not in ids(repo.list(category=EventCategory.BIRTHDAY))

    with pytest.raises(KeyError):
        repo.update(make_item(prefix + "missing"))

    assert repo.delete(b.id) is True
    assert repo.delete(b.id) is False
    assert repo.get(b.id) is None


def check_user_repository(repo, suffix="@example.test", prefix=""):
    user = User(prefix + "u1", "Kari" + suffix, "Kari", "hash", Role.CUSTOMER)
    repo.add(user)

    stored = repo.get_by_email("KARI" + suffix.upper())
    assert stored is not None
    assert stored.id == user.id
    assert stored.email == ("kari" + suffix).lower()
    assert repo.get(user.id).name == "Kari"
    assert repo.get(prefix + "nobody") is None
    with pytest.raises(ValueError):
        repo.add(User(prefix + "u2", "kari" + suffix, "Other", "hash"))


def test_memory_food_item_repository():
    check_food_item_repository(MemoryFoodItemRepository())


def test_memory_user_repository():
    check_user_repository(MemoryUserRepository())


def test_memory_repository_returns_copies():
    repo = MemoryFoodItemRepository()
    repo.add(make_item("x"))
    repo.get("x").name = "changed"
    assert repo.get("x").name == "Fish soup"
