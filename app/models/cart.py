"""Shopping cart rules (C2).

The cart itself is a plain {food_item_id: quantity} dict that the controller keeps
in the session. These functions check quantities and turn the dict into order lines
with current names and prices.
"""

from typing import Optional

from .domain import FoodItem, OrderLine
from .repositories import FoodItemRepository

MAX_QUANTITY = 10_000


def parse_quantity(raw) -> Optional[int]:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def validate_quantity(item: FoodItem, quantity: Optional[int]) -> Optional[str]:
    """An error message, or None when the quantity can be ordered."""
    if quantity is None:
        return "Enter a whole number of portions."
    if quantity < item.min_order_qty:
        return f"Minimum order for {item.name} is {item.min_order_qty}."
    if quantity > MAX_QUANTITY:
        return f"Contact us for orders above {MAX_QUANTITY} portions."
    return None


def cart_lines(cart: dict, food_items: FoodItemRepository) -> tuple[list[OrderLine], list[str]]:
    """Order lines for the items in the cart, at today's prices.

    Items that were deleted or unpublished since they were added are left out,
    with a notice for the customer.
    """
    lines, notices = [], []
    for item_id, quantity in cart.items():
        item = food_items.get(item_id)
        if item is None or not item.published:
            notices.append(
                f"{item.name if item else 'An item'} is no longer on the menu and was removed from your cart."
            )
            continue
        lines.append(OrderLine(item.id, item.name, item.price_nok, quantity))
    return lines, notices


def cart_total(lines: list[OrderLine]) -> int:
    return sum(line.line_total for line in lines)


def cart_portions(cart: dict) -> int:
    return sum(cart.values())
