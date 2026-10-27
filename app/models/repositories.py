"""Repository interfaces.

Controllers depend only on these. There is one implementation per storage
backend: neo4j_repos.py (the real one) and memory.py (used in tests).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from datetime import date

from .domain import Answer, EventCategory, FoodItem, Order, OrderStatus, Question, User
from .images import ImageStore


class FoodItemRepository(ABC):
    @abstractmethod
    def list(
        self, published_only: bool = False, category: Optional[EventCategory] = None
    ) -> list[FoodItem]:
        """Food items sorted by name, optionally only published ones or one event category."""

    @abstractmethod
    def get(self, item_id: str) -> Optional[FoodItem]: ...

    @abstractmethod
    def add(self, item: FoodItem) -> FoodItem: ...

    @abstractmethod
    def update(self, item: FoodItem) -> FoodItem:
        """Replace the stored item with the same id. Raises KeyError if it does not exist."""

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """Return True if an item was deleted."""

    @abstractmethod
    def is_ordered(self, item_id: str) -> bool:
        """True if any order includes this item (then it must not be deleted)."""


class UserRepository(ABC):
    @abstractmethod
    def get(self, user_id: str) -> Optional[User]: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Case-insensitive lookup."""

    @abstractmethod
    def add(self, user: User) -> User:
        """Raises ValueError if the e-mail is already registered."""


class DuplicateReference(ValueError):
    """Another order already has this reference."""


class OrderRepository(ABC):
    @abstractmethod
    def add(self, order: Order) -> Order:
        """Store a new order. Raises DuplicateReference if the reference is taken."""

    @abstractmethod
    def get(self, order_id: str) -> Optional[Order]: ...

    @abstractmethod
    def list_for_customer(self, customer_id: str) -> list[Order]:
        """The customer's orders, newest first."""

    @abstractmethod
    def list(
        self, status: Optional[OrderStatus] = None, event_date: Optional[date] = None
    ) -> list[Order]:
        """All orders, newest first, optionally filtered (for the admin order list, A3)."""


class QuestionRepository(ABC):
    @abstractmethod
    def add(self, question: Question) -> Question: ...

    @abstractmethod
    def list_for_order(self, order_id: str) -> list[Question]:
        """Questions about one order, oldest first (reads like a conversation)."""

    @abstractmethod
    def list_for_customer(self, customer_id: str) -> list[Question]:
        """All questions a customer has asked, oldest first."""

    @abstractmethod
    def answer(self, question_id: str, answer: Answer) -> Question:
        """Set or replace the answer. Raises KeyError for an unknown question."""

    @abstractmethod
    def list_unanswered(self) -> list[Question]:
        """Questions waiting for staff, oldest first (A4)."""


@dataclass
class Repositories:
    food_items: FoodItemRepository
    users: UserRepository
    images: ImageStore
    orders: OrderRepository
    questions: QuestionRepository
