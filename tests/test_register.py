from app.models.domain import Role
from tests.conftest import add_user

GOOD = {"name": "Nora", "email": "Nora@Example.test", "password": "long enough pw", "confirm": "long enough pw"}


def test_register_logs_in_as_customer(client, repositories):
    response = client.post("/account/register", data=GOOD)
    assert response.status_code == 302
    user = repositories.users.get_by_email("nora@example.test")
    assert user.role == Role.CUSTOMER
    assert user.password_hash != GOOD["password"]
    with client.session_transaction() as session:
        assert session["user_id"] == user.id


def test_register_errors_keep_input(client, repositories):
    add_user(repositories, "kari", "kari@example.test", Role.CUSTOMER)
    for data, field_message in [
        ({**GOOD, "email": "kari@example.test"}, "already has an account"),
        ({**GOOD, "email": "not-an-email"}, "valid e-mail"),
        ({**GOOD, "password": "short", "confirm": "short"}, "at least 10"),
        ({**GOOD, "confirm": "something else"}, "do not match"),
        ({**GOOD, "name": " "}, "Enter your name"),
    ]:
        response = client.post("/account/register", data=data)
        assert response.status_code == 400, field_message
        html = response.get_data(as_text=True)
        assert field_message in html
        assert "long enough pw" not in html  # passwords are never echoed back
