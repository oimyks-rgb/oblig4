"""Domain classes for Ekte Mat Online.

Plain dataclasses and enums with no knowledge of storage. Repositories
(see repositories.py) convert between these and the database.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
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

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").capitalize()


class PaymentStatus(str, Enum):
    NOT_PAID = "not_paid"
    DEPOSIT_PAID = "deposit_paid"
    INVOICED = "invoiced"
    PAID = "paid"

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").capitalize()


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


@dataclass
class OrderLine:
    """One food item in an order. Name and price are copied when the order is placed,
    so later menu changes do not alter old orders."""

    food_item_id: str
    name: str
    unit_price_nok: int
    quantity: int

    @property
    def line_total(self) -> int:
        return self.unit_price_nok * self.quantity


@dataclass
class GuestGroup:
    """Allergies or diets for a number of guests, e.g. 2 guests: nut allergy.
    Deliberately no guest names (US-36, GDPR art. 9)."""

    guest_count: int
    note: str


@dataclass
class Order:
    id: str
    reference: str  # shown to customers, e.g. EM-7K3QX9
    customer_id: str
    created_at: datetime
    event_date: date
    guest_count: int
    delivery_street: str
    delivery_postcode: str
    delivery_city: str
    lines: list[OrderLine] = field(default_factory=list)
    guest_groups: list[GuestGroup] = field(default_factory=list)
    event_category: Optional[EventCategory] = None
    phone: str = ""
    comment: str = ""
    status: OrderStatus = OrderStatus.SUBMITTED
    payment_status: PaymentStatus = PaymentStatus.NOT_PAID

    @property
    def total_nok(self) -> int:
        return sum(line.line_total for line in self.lines)

    @property
    def delivery_address(self) -> str:
        return f"{self.delivery_street}, {self.delivery_postcode} {self.delivery_city}"
