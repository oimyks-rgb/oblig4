"""Business rules for food items (A1, US-32, US-33).

Controllers pass raw form values here; this module turns them into a FoodItem
and reports what is wrong, field by field.
"""

import uuid
from collections.abc import Mapping
from typing import Optional

from .domain import Allergen, DietaryLabel, EventCategory, FoodItem

NAME_MAX = 100
DESCRIPTION_MAX = 1000


def new_food_item_id() -> str:
    return uuid.uuid4().hex


def _get_list(form: Mapping, key: str) -> list[str]:
    # Works for both werkzeug MultiDict (request.form) and a plain dict in tests
    if hasattr(form, "getlist"):
        return form.getlist(key)
    value = form.get(key, [])
    return [value] if isinstance(value, str) else list(value)


def _checked(form: Mapping, key: str) -> bool:
    return form.get(key) in ("on", "true", "1", True)


def _positive_int(raw, field, label, errors) -> int:
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        errors[field] = f"{label} must be a whole number."
        return 0
    if value < 1:
        errors[field] = f"{label} must be at least 1."
    return value


def _enum_values(enum, codes, field, errors) -> list:
    """Valid members in the enum's own order; unknown codes give an error."""
    valid = {m.value for m in enum}
    if any(code not in valid for code in codes):
        errors[field] = "Unknown value selected."
    return [m for m in enum if m.value in set(codes)]


def parse_food_item(
    form: Mapping, item_id: Optional[str] = None, image_filename: Optional[str] = None
) -> tuple[FoodItem, dict[str, str]]:
    """Build a FoodItem from form values. Returns the item and a dict of field -> error.

    The item is returned even when there are errors, so the form can be shown again
    with what the user typed.
    """
    errors: dict[str, str] = {}

    name = (form.get("name") or "").strip()
    if not name:
        errors["name"] = "Name is required."
    elif len(name) > NAME_MAX:
        errors["name"] = f"Name can be at most {NAME_MAX} characters."

    description = (form.get("description") or "").strip()
    if len(description) > DESCRIPTION_MAX:
        errors["description"] = f"Description can be at most {DESCRIPTION_MAX} characters."

    price = _positive_int(form.get("price_nok"), "price_nok", "Price", errors)
    min_qty = _positive_int(form.get("min_order_qty"), "min_order_qty", "Minimum order", errors)

    categories = _enum_values(EventCategory, _get_list(form, "event_categories"), "event_categories", errors)
    allergens = _enum_values(Allergen, _get_list(form, "allergens"), "allergens", errors)
    dietary = _enum_values(DietaryLabel, _get_list(form, "dietary_labels"), "dietary_labels", errors)
    no_allergens = _checked(form, "no_allergens")
    published = _checked(form, "published")

    if allergens and no_allergens:
        errors["allergens"] = "Choose allergens or 'contains none of the 14 allergens', not both."
    if DietaryLabel.GLUTEN_FREE in dietary and Allergen.GLUTEN in allergens:
        errors["dietary_labels"] = "An item that contains gluten cannot be labelled gluten-free."

    item = FoodItem(
        id=item_id or new_food_item_id(),
        name=name,
        description=description,
        price_nok=price,
        min_order_qty=min_qty,
        event_categories=categories,
        allergens=allergens,
        dietary_labels=dietary,
        published=published,
        image_filename=image_filename,
        no_allergens=no_allergens,
    )
    if published:
        errors.update(publish_errors(item))
    return item, errors


def publish_errors(item: FoodItem) -> dict[str, str]:
    """Rules an item must meet before customers can see it."""
    errors = {}
    if not item.event_categories:
        errors["event_categories"] = "Choose at least one event category before publishing."
    if not item.allergens and not item.no_allergens:
        errors["allergens"] = (
            "Declare the allergens before publishing, or tick "
            "'contains none of the 14 allergens'."
        )
    return errors
