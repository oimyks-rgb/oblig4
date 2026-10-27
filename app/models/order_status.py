"""The order life cycle (A3), as a state machine.

    submitted -> approved -> in_preparation -> delivered
        |            |              |
        +-> rejected +--> cancelled <+   (submitted can also be cancelled)

delivered, rejected and cancelled are final. See docs/models/order-status.md.
Payment status is independent: staff may set any value at any time.
"""

from typing import Optional

from .domain import OrderStatus as S

ALLOWED: dict[S, set[S]] = {
    S.SUBMITTED: {S.APPROVED, S.REJECTED, S.CANCELLED},
    S.APPROVED: {S.IN_PREPARATION, S.CANCELLED},
    S.IN_PREPARATION: {S.DELIVERED, S.CANCELLED},
    S.DELIVERED: set(),
    S.REJECTED: set(),
    S.CANCELLED: set(),
}

OPEN = {S.SUBMITTED, S.APPROVED, S.IN_PREPARATION}


def next_statuses(status: S) -> list[S]:
    """Allowed next statuses, in the order of the life cycle."""
    return [s for s in S if s in ALLOWED[status]]


def is_final(status: S) -> bool:
    return not ALLOWED[status]


def is_open(status: S) -> bool:
    return status in OPEN


def check_transition(current: S, new: S) -> Optional[str]:
    """An error message, or None if the change is allowed."""
    if new == current:
        return f"The order is already {current.label.lower()}."
    if new not in ALLOWED[current]:
        if is_final(current):
            return f"A {current.label.lower()} order can't be changed."
        return f"An order can't go from {current.label.lower()} to {new.label.lower()}."
    return None
