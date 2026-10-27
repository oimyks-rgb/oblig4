"""In-memory repositories, used by the tests (REPOSITORY_BACKEND = "memory")."""

from copy import deepcopy
from dataclasses import replace
from typing import Optional

from .domain import EventCategory, FoodItem, User
from .repositories import FoodItemRepository, Repositories, UserRepository


class MemoryFoodItemRepository(FoodItemRepository):
    def __init__(self):
        self._items: dict[str, FoodItem] = {}

    def list(self, published_only=False, category: Optional[EventCategory] = None):
        items = [
            i
            for i in self._items.values()
            if (not published_only or i.published)
            and (category is None or category in i.event_categories)
        ]
        return [deepcopy(i) for i in sorted(items, key=lambda i: i.name.lower())]

    def get(self, item_id):
        item = self._items.get(item_id)
        return deepcopy(item) if item else None

    def add(self, item):
        if item.id in self._items:
            raise ValueError(f"Food item {item.id} already exists")
        self._items[item.id] = deepcopy(item)
        return deepcopy(item)

    def update(self, item):
        if item.id not in self._items:
            raise KeyError(item.id)
        self._items[item.id] = deepcopy(item)
        return deepcopy(item)

    def delete(self, item_id):
        return self._items.pop(item_id, None) is not None


class MemoryUserRepository(UserRepository):
    def __init__(self):
        self._users: dict[str, User] = {}

    def get(self, user_id):
        user = self._users.get(user_id)
        return deepcopy(user) if user else None

    def get_by_email(self, email):
        for user in self._users.values():
            if user.email == email.strip().lower():
                return deepcopy(user)
        return None

    def add(self, user):
        if self.get_by_email(user.email):
            raise ValueError(f"E-mail {user.email} is already registered")
        user = replace(user, email=user.email.strip().lower())
        self._users[user.id] = user
        return deepcopy(user)


def memory_repositories() -> Repositories:
    return Repositories(food_items=MemoryFoodItemRepository(), users=MemoryUserRepository())
