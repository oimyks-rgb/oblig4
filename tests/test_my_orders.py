from datetime import datetime, timedelta, timezone

from app.models.domain import Answer, OrderStatus, PaymentStatus, Question, Role
from tests.conftest import add_user, make_item
from tests.test_order_repository import make_order


def place(repositories, order_id, customer_id, minutes_ago=0, **changes):
    order = make_order(order_id, customer_id, "soup", "EM-" + order_id.upper().ljust(6, "X")[:6], minutes_ago)
    for key, value in changes.items():
        setattr(order, key, value)
    return repositories.orders.add(order)


def test_my_orders_requires_login(client):
    assert client.get("/account/").status_code == 302


def test_empty_state(customer_client):
    html = customer_client.get("/account/").get_data(as_text=True)
    assert "You have no orders yet." in html


def test_lists_own_orders_newest_first_with_status(customer_client, repositories):
    repositories.food_items.add(make_item("soup", "Soup"))
    add_user(repositories, "ola", "ola@example.test", Role.CUSTOMER)
    place(repositories, "old", "kari", minutes_ago=60)
    place(repositories, "new", "kari", status=OrderStatus.APPROVED, payment_status=PaymentStatus.DEPOSIT_PAID)
    place(repositories, "olas", "ola")

    html = customer_client.get("/account/").get_data(as_text=True)
    assert html.index("EM-NEWXXX") < html.index("EM-OLDXXX")
    assert "EM-OLASXX" not in html
    assert "Approved" in html and "Deposit paid" in html
    assert "Submitted" in html and "Not paid" in html
    assert "What do the statuses mean?" in html


def test_question_counts(customer_client, repositories):
    repositories.food_items.add(make_item("soup", "Soup"))
    order = place(repositories, "one", "kari")
    t0 = datetime(2026, 11, 1, tzinfo=timezone.utc)
    repositories.questions.add(Question("q1", order.id, "kari", "A?", t0))
    repositories.questions.add(Question("q2", order.id, "kari", "B?", t0 + timedelta(minutes=1)))
    repositories.questions.answer("q1", Answer("Yes", t0, "staff"))
    assert "2 (1 answered)" in customer_client.get("/account/").get_data(as_text=True)
