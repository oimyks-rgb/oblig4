from app.models.cart import cart_lines, cart_portions, cart_total, parse_quantity, validate_quantity
from app.models.memory import MemoryFoodItemRepository
from tests.conftest import make_item


def test_validate_quantity():
    item = make_item(name="Soup", min_order_qty=10)
    assert validate_quantity(item, 10) is None
    assert validate_quantity(item, 9) == "Minimum order for Soup is 10."
    assert "whole number" in validate_quantity(item, parse_quantity("abc"))
    assert "Contact us" in validate_quantity(item, 10_001)


def test_parse_quantity():
    assert parse_quantity(" 12 ") == 12
    assert parse_quantity("1.5") is None
    assert parse_quantity(None) is None


def test_cart_lines_use_current_prices_and_drop_missing_items():
    repo = MemoryFoodItemRepository()
    repo.add(make_item("a", "Soup", price_nok=100))
    repo.add(make_item("b", "Hidden", published=False))

    lines, notices = cart_lines({"a": 12, "b": 10, "gone": 5}, repo)

    assert [(l.food_item_id, l.name, l.unit_price_nok, l.quantity) for l in lines] == [("a", "Soup", 100, 12)]
    assert len(notices) == 2
    assert "Hidden is no longer on the menu" in notices[0]
    assert cart_total(lines) == 1200
    assert cart_portions({"a": 12, "b": 3}) == 15
