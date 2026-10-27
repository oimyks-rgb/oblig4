"""In-memory repositories, used by the tests (REPOSITORY_BACKEND = "memory")."""

import time
from copy import deepcopy
from dataclasses import replace
from typing import Optional

from .domain import EventCategory, FoodItem, Order, User
from .images import ImageStore
from .repositories import (
    DuplicateReference,
    FoodItemRepository,
    OrderRepository,
    Repositories,
    UserRepository,
)


class MemoryFoodItemRepository(FoodItemRepository):
    def __init__(self, orders: "MemoryOrderRepository | None" = None):
        self._items: dict[str, FoodItem] = {}
        self._orders = orders

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

    def is_ordered(self, item_id):
        return self._orders is not None and self._orders.includes_item(item_id)


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


class MemoryImageStore(ImageStore):
    def __init__(self):
        self._files: dict[str, tuple[bytes, float]] = {}

    def _write(self, name, data):
        self._files[name] = (data, time.time())

    def _read(self, name):
        entry = self._files.get(name)
        return entry[0] if entry else None

    def _exists(self, name):
        return name in self._files

    def _delete(self, name):
        self._files.pop(name, None)

    def cleanup_drafts(self, max_age):
        cutoff = time.time() - max_age.total_seconds()
        old = [n for n, (_, t) in self._files.items() if n.startswith("draft-") and t < cutoff]
        for name in old:
            del self._files[name]
        return len(old)


class MemoryOrderRepository(OrderRepository):
    def __init__(self):
        self._orders: dict[str, Order] = {}

    def add(self, order):
        if any(o.reference == order.reference for o in self._orders.values()):
            raise DuplicateReference(order.reference)
        self._orders[order.id] = deepcopy(order)
        return deepcopy(order)

    def get(self, order_id):
        order = self._orders.get(order_id)
        return deepcopy(order) if order else None

    def _newest_first(self, orders):
        return [deepcopy(o) for o in sorted(orders, key=lambda o: o.created_at, reverse=True)]

    def list_for_customer(self, customer_id):
        return self._newest_first(o for o in self._orders.values() if o.customer_id == customer_id)

    def list(self, status=None, event_date=None):
        return self._newest_first(
            o
            for o in self._orders.values()
            if (status is None or o.status == status)
            and (event_date is None or o.event_date == event_date)
        )

    def includes_item(self, item_id):
        return any(line.food_item_id == item_id for o in self._orders.values() for line in o.lines)


def memory_repositories(images: ImageStore | None = None) -> Repositories:
    orders = MemoryOrderRepository()
    return Repositories(
        food_items=MemoryFoodItemRepository(orders),
        users=MemoryUserRepository(),
        images=images or MemoryImageStore(),
        orders=orders,
    )
