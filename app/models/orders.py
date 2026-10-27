"""Order rules (C3, US-02, US-36): checking the checkout form and making references."""

import re
import secrets
import uuid
from collections.abc import Mapping
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from .domain import EventCategory, GuestGroup, Order, OrderLine, User
from .repositories import DuplicateReference, FoodItemRepository, OrderRepository

# ASSUMPTION: the kitchen needs 3 days' notice. Change here if Ekte Mat decides otherwise.
MIN_LEAD_DAYS = 3
MAX_DAYS_AHEAD = 365
MAX_GUESTS = 2000
GROUP_NOTE_MAX = 200
COMMENT_MAX = 1000

_REFERENCE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # no 0/O/1/I
_POSTCODE = re.compile(r"^\d{4}$")
_PHONE = re.compile(r"^\+?[\d ]{8,15}$")


def new_reference() -> str:
    return "EM-" + "".join(secrets.choice(_REFERENCE_ALPHABET) for _ in range(6))


def earliest_event_date(today: date) -> date:
    return today + timedelta(days=MIN_LEAD_DAYS)


def _get_list(form: Mapping, key: str) -> list[str]:
    if hasattr(form, "getlist"):
        return form.getlist(key)
    value = form.get(key, [])
    return [value] if isinstance(value, str) else list(value)


def _int(raw):
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def parse_guest_groups(form: Mapping, errors: dict) -> list[GuestGroup]:
    """Rows of (count, note). Completely empty rows are ignored."""
    groups = []
    for count_raw, note in zip(_get_list(form, "group_count"), _get_list(form, "group_note")):
        count_raw, note = (count_raw or "").strip(), (note or "").strip()
        if not count_raw and not note:
            continue
        count = _int(count_raw)
        if count is None or count < 1:
            errors["guest_groups"] = "Each guest group needs a number of guests (at least 1)."
        elif not note:
            errors["guest_groups"] = "Describe the allergy or diet for each guest group."
        elif len(note) > GROUP_NOTE_MAX:
            errors["guest_groups"] = f"Keep each note under {GROUP_NOTE_MAX} characters."
        groups.append(GuestGroup(count or 0, note))
    return groups


def parse_checkout(
    form: Mapping,
    lines: list[OrderLine],
    customer: User,
    today: date,
    food_items: FoodItemRepository,
) -> tuple[Order, dict[str, str]]:
    """Build an Order from the checkout form and the cart lines. Returns (order, errors)."""
    errors: dict[str, str] = {}

    event_date = None
    try:
        event_date = date.fromisoformat((form.get("event_date") or "").strip())
    except ValueError:
        errors["event_date"] = "Choose the date of the event."
    if event_date:
        if event_date < earliest_event_date(today):
            errors["event_date"] = f"We need at least {MIN_LEAD_DAYS} days' notice. Choose a later date."
        elif event_date > today + timedelta(days=MAX_DAYS_AHEAD):
            errors["event_date"] = "We take orders up to a year ahead."

    guests = _int(form.get("guest_count"))
    if guests is None or guests < 1:
        errors["guest_count"] = "Enter the number of guests."
    elif guests > MAX_GUESTS:
        errors["guest_count"] = f"Contact us directly for events above {MAX_GUESTS} guests."

    street = (form.get("delivery_street") or "").strip()
    postcode = (form.get("delivery_postcode") or "").strip()
    city = (form.get("delivery_city") or "").strip()
    if not street:
        errors["delivery_street"] = "Enter the delivery address."
    if not _POSTCODE.match(postcode):
        errors["delivery_postcode"] = "Enter a 4-digit postcode."
    if not city:
        errors["delivery_city"] = "Enter the town or city."

    phone = (form.get("phone") or "").strip()
    if phone and not _PHONE.match(phone):
        errors["phone"] = "Enter a phone number with 8 to 15 digits."

    category = None
    category_raw = (form.get("event_category") or "").strip()
    if category_raw:
        try:
            category = EventCategory(category_raw)
        except ValueError:
            errors["event_category"] = "Choose a type of event from the list."

    comment = (form.get("comment") or "").strip()
    if len(comment) > COMMENT_MAX:
        errors["comment"] = f"Keep the comment under {COMMENT_MAX} characters."

    groups = parse_guest_groups(form, errors)
    if guests and "guest_groups" not in errors and sum(g.guest_count for g in groups) > guests:
        errors["guest_groups"] = "The guest groups add up to more guests than the event has."

    if not lines:
        errors["cart"] = "Your cart is empty."
    for line in lines:
        item = food_items.get(line.food_item_id)
        if item is None or not item.published:
            errors["cart"] = f"{line.name} is no longer on the menu. Check your cart."
        elif line.quantity < item.min_order_qty:
            errors["cart"] = f"Minimum order for {item.name} is {item.min_order_qty}. Check your cart."

    order = Order(
        id=uuid.uuid4().hex,
        reference=new_reference(),
        customer_id=customer.id,
        created_at=datetime.now(timezone.utc),
        event_date=event_date or today,
        guest_count=guests or 0,
        delivery_street=street,
        delivery_postcode=postcode,
        delivery_city=city,
        lines=list(lines),
        guest_groups=groups,
        event_category=category,
        phone=phone,
        comment=comment,
    )
    return order, errors


def place_order(orders: OrderRepository, order: Order) -> Order:
    """Store the order, picking a new reference in the unlikely case it is taken."""
    for _ in range(5):
        try:
            return orders.add(order)
        except DuplicateReference:
            order = replace(order, reference=new_reference())
    raise RuntimeError("Could not find a free order reference")
