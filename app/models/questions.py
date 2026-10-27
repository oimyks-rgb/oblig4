"""Questions about orders (C5): checking the text and creating questions."""

import uuid
from datetime import datetime, timezone

from .domain import Answer, Order, Question, User

TEXT_MAX = 1000
ANSWER_MAX = 2000


def parse_question(text: str) -> tuple[str, dict[str, str]]:
    """The cleaned text and a field -> message dict."""
    text = (text or "").strip()
    if not text:
        return text, {"text": "Write your question."}
    if len(text) > TEXT_MAX:
        return text, {"text": f"Keep the question under {TEXT_MAX} characters."}
    return text, {}


def new_question(order: Order, customer: User, text: str) -> Question:
    return Question(
        id=uuid.uuid4().hex,
        order_id=order.id,
        customer_id=customer.id,
        text=text,
        asked_at=datetime.now(timezone.utc),
    )


def parse_answer(text: str) -> tuple[str, dict[str, str]]:
    """Staff answers (A4): required, at most ANSWER_MAX characters."""
    text = (text or "").strip()
    if not text:
        return text, {"answer": "Write an answer."}
    if len(text) > ANSWER_MAX:
        return text, {"answer": f"Keep the answer under {ANSWER_MAX} characters."}
    return text, {}


def new_answer(text: str, staff: User) -> Answer:
    return Answer(text=text, answered_at=datetime.now(timezone.utc), answered_by_id=staff.id)
