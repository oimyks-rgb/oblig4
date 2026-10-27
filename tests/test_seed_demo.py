from datetime import date

from app.models.domain import Role
from seed import DEMO_ORDER_ID, FOOD_ITEMS, seed_demo_order
from tests.conftest import add_user


def test_demo_order_is_created_once(repositories):
    for item in FOOD_ITEMS:
        repositories.food_items.add(item)
    add_user(repositories, "seed-kari", "kari.nordmann@ektemat.test", Role.CUSTOMER)
    add_user(repositories, "seed-admin", "admin@ektemat.test", Role.ADMIN)

    assert seed_demo_order(repositories, today=date(2026, 11, 1)) is True
    order = repositories.orders.get(DEMO_ORDER_ID)
    assert order.reference == "EM-DEMO01"
    assert order.event_date == date(2026, 12, 1)
    [question] = repositories.questions.list_for_order(DEMO_ORDER_ID)
    assert question.is_answered

    assert seed_demo_order(repositories) is False
    assert len(repositories.orders.list()) == 1


def test_demo_order_needs_seed_users(repositories):
    assert seed_demo_order(repositories) is False
