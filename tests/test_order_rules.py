from datetime import date, timedelta

import pytest
from werkzeug.datastructures import MultiDict

from app.models.domain import EventCategory, OrderLine, OrderStatus, PaymentStatus, Role, User
from app.models.memory import MemoryFoodItemRepository, MemoryOrderRepository
from app.models.orders import MIN_LEAD_DAYS, new_reference, parse_checkout, place_order
from tests.conftest import make_item

TODAY = date(2026, 11, 2)
CUSTOMER = User("kari", "kari@example.test", "Kari", "hash", Role.CUSTOMER)


@pytest.fixture
def food_items():
    repo = MemoryFoodItemRepository()
    repo.add(make_item("soup", "Soup", price_nok=165, min_order_qty=10))
    return repo


LINES = [OrderLine("soup", "Soup", 165, 20)]


def form(**overrides):
    data = {
        "event_date": (TODAY + timedelta(days=10)).isoformat(),
        "guest_count": "20",
        "delivery_street": "Bryggen 1",
        "delivery_postcode": "5003",
        "delivery_city": "Bergen",
        "phone": "+47 900 00 000",
        "event_category": "conference",
        "group_count": ["2", "", "1"],
        "group_note": ["nut allergy", "", "vegan"],
        "comment": "Ring the bell",
    }
    data.update(overrides)
    return MultiDict([(k, v) for k, vs in data.items() for v in (vs if isinstance(vs, list) else [vs])])


def check(food_items, lines=LINES, **overrides):
    return parse_checkout(form(**overrides), lines, CUSTOMER, TODAY, food_items)


def test_valid_checkout(food_items):
    order, errors = check(food_items)
    assert errors == {}
    assert order.customer_id == "kari"
    assert order.event_date == TODAY + timedelta(days=10)
    assert order.event_category == EventCategory.CONFERENCE
    assert order.guest_count == 20
    assert order.delivery_address == "Bryggen 1, 5003 Bergen"
    assert [(g.guest_count, g.note) for g in order.guest_groups] == [(2, "nut allergy"), (1, "vegan")]
    assert order.total_nok == 3300
    assert order.status == OrderStatus.SUBMITTED
    assert order.payment_status == PaymentStatus.NOT_PAID
    assert order.reference.startswith("EM-") and len(order.reference) == 9


def test_event_date_rules(food_items):
    assert "event_date" in check(food_items, event_date="")[1]
    assert "event_date" in check(food_items, event_date="31.12.2026")[1]
    too_soon = (TODAY + timedelta(days=MIN_LEAD_DAYS - 1)).isoformat()
    assert "notice" in check(food_items, event_date=too_soon)[1]["event_date"]
    assert check(food_items, event_date=(TODAY + timedelta(days=MIN_LEAD_DAYS)).isoformat())[1] == {}
    assert "year" in check(food_items, event_date=(TODAY + timedelta(days=400)).isoformat())[1]["event_date"]


@pytest.mark.parametrize("bad", ["", "0", "abc", "2001"])
def test_guest_count(food_items, bad):
    assert "guest_count" in check(food_items, guest_count=bad)[1]


def test_address_and_phone(food_items):
    errors = check(food_items, delivery_street=" ", delivery_postcode="503", delivery_city="", phone="12")[1]
    assert {"delivery_street", "delivery_postcode", "delivery_city", "phone"} <= set(errors)
    assert check(food_items, phone="")[1] == {}


def test_unknown_event_category(food_items):
    assert "event_category" in check(food_items, event_category="funeral")[1]
    assert check(food_items, event_category="")[0].event_category is None


def test_guest_groups(food_items):
    assert "guest_groups" in check(food_items, group_count=["2"], group_note=[""])[1]
    assert "guest_groups" in check(food_items, group_count=["0"], group_note=["vegan"])[1]
    assert "guest_groups" in check(food_items, group_count=["x"], group_note=["vegan"])[1]
    assert "guest_groups" in check(food_items, group_count=["15", "10"], group_note=["a", "b"])[1]
    assert check(food_items, group_count=["", ""], group_note=["", ""])[0].guest_groups == []


def test_cart_must_be_valid(food_items):
    assert "cart" in check(food_items, lines=[])[1]
    assert "Minimum order" in check(food_items, lines=[OrderLine("soup", "Soup", 165, 5)])[1]["cart"]
    assert "no longer" in check(food_items, lines=[OrderLine("gone", "Gone", 10, 5)])[1]["cart"]


def test_references():
    refs = {new_reference() for _ in range(200)}
    assert len(refs) == 200
    assert not any(ch in r[3:] for r in refs for ch in "01OI")


def test_place_order_retries_taken_reference(food_items):
    orders = MemoryOrderRepository()
    first, _ = check(food_items)
    place_order(orders, first)
    second, _ = check(food_items)
    second.reference = first.reference
    stored = place_order(orders, second)
    assert stored.reference != first.reference
