from datetime import datetime, timezone

import pytest

from app.models.domain import Answer, Role
from tests.conftest import add_user, log_in, make_item
from tests.test_order_repository import make_order


@pytest.fixture
def order(repositories):
    repositories.food_items.add(make_item("soup", "Soup"))
    add_user(repositories, "kari", "kari@example.test", Role.CUSTOMER)
    return repositories.orders.add(make_order("o1", "kari", "soup", "EM-ABCDEF"))


def ask(client, order_id, text):
    return client.post(f"/account/orders/{order_id}/questions", data={"text": text})


def test_owner_can_ask_and_sees_waiting(client, repositories, order):
    log_in(client, "kari@example.test")
    response = ask(client, order.id, "Can you deliver at 11?")
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/account/orders/{order.id}#questions")

    [question] = repositories.questions.list_for_order(order.id)
    assert question.text == "Can you deliver at 11?" and question.customer_id == "kari"
    html = client.get(f"/account/orders/{order.id}").get_data(as_text=True)
    assert "Can you deliver at 11?" in html
    assert "Waiting for an answer from Ekte Mat." in html


def test_answer_is_shown(client, repositories, order):
    log_in(client, "kari@example.test")
    ask(client, order.id, "Can you deliver at 11?")
    [question] = repositories.questions.list_for_order(order.id)
    repositories.questions.answer(question.id, Answer("Yes, 11 is fine.", datetime.now(timezone.utc), "staff"))
    html = client.get(f"/account/orders/{order.id}").get_data(as_text=True)
    assert "Ekte Mat answered" in html and "Yes, 11 is fine." in html
    assert "Waiting for an answer" not in html


def test_invalid_question_keeps_text(client, repositories, order):
    log_in(client, "kari@example.test")
    assert ask(client, order.id, "  ").status_code == 400
    response = ask(client, order.id, "x" * 1001)
    assert response.status_code == 400
    assert "x" * 1001 in response.get_data(as_text=True)
    assert repositories.questions.list_for_order(order.id) == []


def test_other_customer_gets_404(client, repositories, order):
    add_user(repositories, "ola", "ola@example.test", Role.CUSTOMER)
    log_in(client, "ola@example.test")
    assert client.get(f"/account/orders/{order.id}").status_code == 404
    assert ask(client, order.id, "Sneaky?").status_code == 404
    assert repositories.questions.list_for_order(order.id) == []


def test_admin_sees_order_but_cannot_ask(client, repositories, order):
    add_user(repositories, "admin", "admin@example.test", Role.ADMIN)
    log_in(client, "admin@example.test")
    html = client.get(f"/account/orders/{order.id}").get_data(as_text=True)
    assert "Questions about this order" in html
    assert "Send question" not in html
    assert ask(client, order.id, "Hello").status_code == 404


def test_status_description_is_shown(client, order):
    log_in(client, "kari@example.test")
    assert "Ekte Mat has received your order" in client.get(f"/account/orders/{order.id}").get_data(as_text=True)
