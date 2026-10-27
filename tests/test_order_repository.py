"""Order repository contract, shared by the memory and Neo4j tests."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.domain import EventCategory, GuestGroup, Order, OrderLine, OrderStatus
from app.models.memory import memory_repositories
from app.models.repositories import DuplicateReference
from tests.conftest import add_user, make_item


def make_order(order_id, customer_id, item_id, reference, created_minutes_ago=0, event_date=date(2027, 1, 15)):
    return Order(
        id=order_id,
        reference=reference,
        customer_id=customer_id,
        created_at=datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc) - timedelta(minutes=created_minutes_ago),
        event_date=event_date,
        guest_count=20,
        delivery_street="Bryggen 1",
        delivery_postcode="5003",
        delivery_city="Bergen",
        lines=[OrderLine(item_id, "Soup", 165, 20)],
        guest_groups=[GuestGroup(2, "nut allergy"), GuestGroup(1, "vegan")],
        event_category=EventCategory.CONFERENCE,
        phone="+47 900 00 000",
        comment="Ring the bell",
    )


def check_order_repository(repos, prefix="", email_suffix="@example.test"):
    from app.models.domain import Role

    kari = add_user(repos, prefix + "kari", "kari" + email_suffix, Role.CUSTOMER)
    ola = add_user(repos, prefix + "ola", "ola" + email_suffix, Role.CUSTOMER)
    repos.food_items.add(make_item(prefix + "soup", prefix + "Soup"))
    item_id = prefix + "soup"
    assert repos.food_items.is_ordered(item_id) is False

    older = make_order(prefix + "o1", kari.id, item_id, prefix.upper() + "EM-AAAAA1", created_minutes_ago=60)
    newer = make_order(prefix + "o2", kari.id, item_id, prefix.upper() + "EM-AAAAA2", event_date=date(2027, 2, 1))
    other = make_order(prefix + "o3", ola.id, item_id, prefix.upper() + "EM-AAAAA3")
    for order in (older, newer, other):
        repos.orders.add(order)

    stored = repos.orders.get(older.id)
    assert stored == older
    assert stored.total_nok == 3300
    assert repos.orders.get(prefix + "missing") is None

    assert [o.id for o in repos.orders.list_for_customer(kari.id)] == [newer.id, older.id]
    ids = {o.id for o in repos.orders.list()}
    assert {older.id, newer.id, other.id} <= ids
    assert newer.id not in {o.id for o in repos.orders.list(event_date=date(2027, 1, 15))}
    assert older.id in {o.id for o in repos.orders.list(status=OrderStatus.SUBMITTED)}
    assert older.id not in {o.id for o in repos.orders.list(status=OrderStatus.DELIVERED)}

    duplicate = make_order(prefix + "o4", kari.id, item_id, older.reference)
    with pytest.raises(DuplicateReference):
        repos.orders.add(duplicate)

    assert repos.food_items.is_ordered(item_id) is True


def test_memory_order_repository():
    check_order_repository(memory_repositories())
