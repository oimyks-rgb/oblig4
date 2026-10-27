"""Question repository contract, shared by the memory and Neo4j tests."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.domain import Answer, Question, Role
from app.models.memory import memory_repositories
from tests.conftest import add_user, make_item
from tests.test_order_repository import make_order

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def check_question_repository(repos, prefix="", email_suffix="@example.test"):
    kari = add_user(repos, prefix + "kari", "kari" + email_suffix, Role.CUSTOMER)
    ola = add_user(repos, prefix + "ola", "ola" + email_suffix, Role.CUSTOMER)
    staff = add_user(repos, prefix + "staff", "staff" + email_suffix, Role.ADMIN)
    repos.food_items.add(make_item(prefix + "soup", prefix + "Soup"))
    order_k = repos.orders.add(make_order(prefix + "ok", kari.id, prefix + "soup", prefix.upper() + "EM-QQQQQ1"))
    order_o = repos.orders.add(make_order(prefix + "oo", ola.id, prefix + "soup", prefix.upper() + "EM-QQQQQ2"))

    later = repos.questions.add(Question(prefix + "q2", order_k.id, kari.id, "Second?", T0 + timedelta(hours=1)))
    first = repos.questions.add(Question(prefix + "q1", order_k.id, kari.id, "First?", T0))
    other = repos.questions.add(Question(prefix + "q3", order_o.id, ola.id, "Ola's?", T0))
    assert first.text == "First?" and first.answer is None and first.asked_at == T0

    assert [q.id for q in repos.questions.list_for_order(order_k.id)] == [first.id, later.id]
    assert [q.id for q in repos.questions.list_for_customer(kari.id)] == [first.id, later.id]
    assert [q.id for q in repos.questions.list_for_customer(ola.id)] == [other.id]

    answered = repos.questions.answer(first.id, Answer("Yes.", T0 + timedelta(hours=2), staff.id))
    assert answered.is_answered
    assert answered.answer == Answer("Yes.", T0 + timedelta(hours=2), staff.id)

    replaced = repos.questions.answer(first.id, Answer("Yes, gladly.", T0 + timedelta(hours=3), staff.id))
    assert replaced.answer.text == "Yes, gladly."
    assert repos.questions.list_for_order(order_k.id)[0].answer.text == "Yes, gladly."

    unanswered = {q.id for q in repos.questions.list_unanswered()}
    assert {later.id, other.id} <= unanswered
    assert first.id not in unanswered

    with pytest.raises(KeyError):
        repos.questions.answer(prefix + "missing", Answer("x", T0, staff.id))


def test_memory_question_repository():
    check_question_repository(memory_repositories())
