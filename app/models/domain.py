"""Domain classes for Ekte Mat Online.

Plain dataclasses and enums with no knowledge of storage. Repositories
(see repositories.py) convert between these and the database.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EventCategory(str, Enum):
    BIRTHDAY = "birthday"
    CONFIRMATION = "confirmation"
    WEDDING = "wedding"
    CONFERENCE = "conference"
    CHRISTMAS_PARTY = "christmas_party"  # julebord
    LUNCH_MEETING = "lunch_meeting"

    @property
    def label(self) -> str:
        return _EVENT_LABELS[self]


_EVENT_LABELS = {
    EventCategory.BIRTHDAY: "Birthday",
    EventCategory.CONFIRMATION: "Confirmation",
    EventCategory.WEDDING: "Wedding",
    EventCategory.CONFERENCE: "Conference",
    EventCategory.CHRISTMAS_PARTY: "Christmas party (julebord)",
    EventCategory.LUNCH_MEETING: "Lunch meeting",
}


class Allergen(str, Enum):
    """The 14 allergens that must be declared in Norway/EU."""

    GLUTEN = "gluten"
    CRUSTACEANS = "crustaceans"
    EGGS = "eggs"
    FISH = "fish"
    PEANUTS = "peanuts"
    SOY = "soy"
    MILK = "milk"
    NUTS = "nuts"
    CELERY = "celery"
    MUSTARD = "mustard"
    SESAME = "sesame"
    SULPHITES = "sulphites"
    LUPIN = "lupin"
    MOLLUSCS = "molluscs"

    @property
    def label(self) -> str:
        return self.value.capitalize()


class DietaryLabel(str, Enum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    LACTOSE_FREE = "lactose_free"
    HALAL = "halal"

    @property
    def label(self) -> str:
        return self.value.replace("_", "-").capitalize()


class OrderStatus(str, Enum):
    """Order life cycle from the assignment (A3): submitted -> approved ->
    in_preparation -> delivered, or rejected / cancelled."""

    SUBMITTED = "submitted"
    APPROVED = "approved"
    IN_PREPARATION = "in_preparation"
    DELIVERED = "delivered"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    NOT_PAID = "not_paid"
    DEPOSIT_PAID = "deposit_paid"
    INVOICED = "invoiced"
    PAID = "paid"


class Role(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"


@dataclass
class FoodItem:
    id: str
    name: str
    description: str
    price_nok: int  # price per unit (portion) in whole NOK
    min_order_qty: int
    event_categories: list[EventCategory] = field(default_factory=list)
    allergens: list[Allergen] = field(default_factory=list)
    dietary_labels: list[DietaryLabel] = field(default_factory=list)
    published: bool = False
    image_filename: Optional[str] = None
    # Staff confirmed the item contains none of the 14 allergens (US-33)
    no_allergens: bool = False


@dataclass
class User:
    id: str
    email: str
    name: str
    password_hash: str
    role: Role = Role.CUSTOMER

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN
