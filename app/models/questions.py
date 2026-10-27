"""Questions about orders (C5): checking the text and creating questions."""

import uuid
from datetime import datetime, timezone

from .domain import Order, Question, User

TEXT_MAX = 1000


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
