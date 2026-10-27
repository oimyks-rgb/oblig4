from app.models.questions import TEXT_MAX, parse_question


def test_question_text_is_trimmed():
    assert parse_question("  Can you deliver earlier?  ") == ("Can you deliver earlier?", {})


def test_empty_question_is_rejected():
    assert "text" in parse_question("   ")[1]
    assert "text" in parse_question(None)[1]


def test_long_question_is_rejected():
    assert "text" in parse_question("x" * (TEXT_MAX + 1))[1]
    assert parse_question("x" * TEXT_MAX)[1] == {}
