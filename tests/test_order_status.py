import pytest

from app.models.domain import OrderStatus as S
from app.models.order_status import check_transition, is_final, is_open, next_statuses

ALLOWED = {
    (S.SUBMITTED, S.APPROVED), (S.SUBMITTED, S.REJECTED), (S.SUBMITTED, S.CANCELLED),
    (S.APPROVED, S.IN_PREPARATION), (S.APPROVED, S.CANCELLED),
    (S.IN_PREPARATION, S.DELIVERED), (S.IN_PREPARATION, S.CANCELLED),
}


@pytest.mark.parametrize("current", list(S))
@pytest.mark.parametrize("new", list(S))
def test_every_transition(current, new):
    error = check_transition(current, new)
    if (current, new) in ALLOWED:
        assert error is None
    else:
        assert error, f"{current} -> {new} should be refused"


def test_messages():
    assert check_transition(S.DELIVERED, S.APPROVED) == "A delivered order can't be changed."
    assert check_transition(S.SUBMITTED, S.DELIVERED) == "An order can't go from submitted to delivered."
    assert check_transition(S.APPROVED, S.APPROVED) == "The order is already approved."


def test_next_statuses_follow_the_life_cycle():
    assert next_statuses(S.SUBMITTED) == [S.APPROVED, S.REJECTED, S.CANCELLED]
    assert next_statuses(S.IN_PREPARATION) == [S.DELIVERED, S.CANCELLED]
    assert next_statuses(S.DELIVERED) == []


def test_final_and_open():
    assert {s for s in S if is_final(s)} == {S.DELIVERED, S.REJECTED, S.CANCELLED}
    assert {s for s in S if is_open(s)} == {S.SUBMITTED, S.APPROVED, S.IN_PREPARATION}
