from datetime import datetime, timedelta, timezone

import pytest

from app.models.domain import Question, Role
from tests.conftest import add_user, log_in, make_item
from tests.test_order_repository import make_order
from tests.test_checkout import CHECKOUT

T0 = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)


@pytest.fixture
def setup(repositories):
    repositories.food_items.add(make_item("soup", "Soup"))
    if not repositories.users.get_by_email("kari@example.test"):  # customer_client may have added her
        add_user(repositories, "kari", "kari@example.test", Role.CUSTOMER)
    o1 = repositories.orders.add(make_order("o1", "kari", "soup", "EM-AAAAA1"))
    o2 = repositories.orders.add(make_order("o2", "kari", "soup", "EM-AAAAA2"))
    repositories.questions.add(Question("q-new", o1.id, "kari", "Newer question?", T0 + timedelta(hours=1)))
    repositories.questions.add(Question("q-old", o2.id, "kari", "Older question?", T0))
    return o1, o2


def answer(client, question_id, order_id, text):
    return client.post(f"/admin/questions/{question_id}/answer", data={"order_id": order_id, "answer": text})


def test_inbox_lists_unanswered_oldest_first_with_count(admin_client, setup):
    html = admin_client.get("/admin/questions/").get_data(as_text=True)
    assert html.index("Older question?") < html.index("Newer question?")
    assert '<span class="count">2</span>' in html


def test_answer_and_edit(admin_client, repositories, setup):
    o1, _ = setup
    response = answer(admin_client, "q-new", o1.id, "Yes, we can.")
    assert response.headers["Location"].endswith(f"/admin/orders/{o1.id}#q-q-new")
    [q] = repositories.questions.list_for_order(o1.id)
    assert q.answer.text == "Yes, we can." and q.answer.answered_by_id == "admin"
    html = admin_client.get("/admin/questions/").get_data(as_text=True)
    assert "Newer question?" not in html and '<span class="count">1</span>' in html

    answer(admin_client, "q-new", o1.id, "Yes, at 11:30.")
    assert repositories.questions.list_for_order(o1.id)[0].answer.text == "Yes, at 11:30."


def test_empty_answer_is_refused(admin_client, repositories, setup):
    o1, _ = setup
    answer(admin_client, "q-new", o1.id, "   ")
    assert repositories.questions.list_for_order(o1.id)[0].answer is None
    assert "Write an answer." in admin_client.get(f"/admin/orders/{o1.id}").get_data(as_text=True)


def test_question_must_belong_to_order(admin_client, setup):
    o1, _ = setup
    assert answer(admin_client, "q-old", o1.id, "Wrong order").status_code == 404
    assert answer(admin_client, "q-old", "nope", "Unknown order").status_code == 404


def test_customer_cannot_answer(customer_client, setup):
    o1, _ = setup
    assert answer(customer_client, "q-new", o1.id, "I answer myself").status_code == 403
    assert customer_client.get("/admin/questions/").status_code == 403


def test_end_to_end_customer_sees_status_payment_and_answer(client, repositories):
    repositories.food_items.add(make_item("soup", "Soup", min_order_qty=10))
    add_user(repositories, "kari", "kari@example.test", Role.CUSTOMER)
    add_user(repositories, "admin", "admin@example.test", Role.ADMIN)

    log_in(client, "kari@example.test")
    client.post("/cart/add", data={"item_id": "soup", "quantity": "20"})
    client.post("/order/checkout", data=CHECKOUT)
    [order] = repositories.orders.list()
    client.post(f"/account/orders/{order.id}/questions", data={"text": "Parking at the venue?"})
    client.post("/account/logout")

    log_in(client, "admin@example.test")
    client.post(f"/admin/orders/{order.id}/status", data={"status": "approved"})
    client.post(f"/admin/orders/{order.id}/payment", data={"payment_status": "deposit_paid"})
    [question] = repositories.questions.list_for_order(order.id)
    answer(client, question.id, order.id, "Yes, by the back door.")
    client.post("/account/logout")

    log_in(client, "kari@example.test")
    html = client.get("/account/").get_data(as_text=True)
    assert "Approved" in html and "Deposit paid" in html and "1 (1 answered)" in html
    html = client.get(f"/account/orders/{order.id}").get_data(as_text=True)
    assert "Yes, by the back door." in html
