from app.models.domain import Role
from tests.conftest import add_user, log_in


def test_admin_login_redirects_to_admin(client, repositories):
    add_user(repositories, "admin", "admin@example.test", Role.ADMIN)
    response = log_in(client, "ADMIN@example.test")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/")


def test_wrong_password_is_rejected_without_saying_which_field(client, repositories):
    add_user(repositories, "admin", "admin@example.test", Role.ADMIN)
    response = log_in(client, "admin@example.test", "wrong")
    assert response.status_code == 401
    assert "Wrong e-mail or password." in response.get_data(as_text=True)
    assert client.get("/admin/").status_code == 302


def test_unknown_email_is_rejected(client):
    assert log_in(client, "nobody@example.test").status_code == 401


def test_next_is_followed_only_within_the_site(client, repositories):
    add_user(repositories, "admin", "admin@example.test", Role.ADMIN)
    response = log_in(client, "admin@example.test", next="/admin/food-items/")
    assert response.headers["Location"].endswith("/admin/food-items/")

    for evil in ("https://evil.example/", "//evil.example/"):
        response = log_in(client, "admin@example.test", next=evil)
        assert "evil" not in response.headers["Location"]


def test_logout(admin_client):
    assert admin_client.get("/admin/food-items/").status_code == 200
    admin_client.post("/account/logout")
    assert admin_client.get("/admin/food-items/").status_code == 302


def test_customer_cannot_open_admin(customer_client):
    assert customer_client.get("/admin/food-items/").status_code == 403
    assert customer_client.post("/admin/food-items/new", data={"name": "x"}).status_code == 403
