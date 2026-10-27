from datetime import date, timedelta

import pytest

from app.models.domain import Role
from app.models.orders import MIN_LEAD_DAYS
from tests.conftest import add_user, log_in, make_item

EVENT = (date.today() + timedelta(days=MIN_LEAD_DAYS + 7)).isoformat()
CHECKOUT = {
    "event_date": EVENT,
    "guest_count": "25",
    "event_category": "birthday",
    "delivery_street": "Bryggen 1",
    "delivery_postcode": "5003",
    "delivery_city": "Bergen",
    "group_count": ["2", ""],
    "group_note": ["nut allergy", ""],
}


@pytest.fixture
def menu(repositories):
    repositories.food_items.add(make_item("soup", "Soup", price_nok=165, min_order_qty=10))


def fill_cart(client, quantity="20"):
    client.post("/cart/add", data={"item_id": "soup", "quantity": quantity})


def test_checkout_requires_login_and_cart_survives_login(client, repositories, menu):
    add_user(repositories, "kari", "kari@example.test", Role.CUSTOMER)
    fill_cart(client)
    response = client.get("/order/checkout")
    assert response.status_code == 302 and "/account/login" in response.headers["Location"]

    response = log_in(client, "kari@example.test", next="/order/checkout")
    assert response.headers["Location"].endswith("/order/checkout")
    assert client.get("/order/checkout").status_code == 200


def test_cart_survives_registration(client, menu):
    fill_cart(client)
    client.post("/account/register?next=/order/checkout",
                data={"name": "Nora", "email": "nora@example.test", "password": "long enough pw", "confirm": "long enough pw"})
    assert client.get("/order/checkout").status_code == 200


def test_empty_cart_redirects_to_menu(customer_client):
    response = customer_client.get("/order/checkout")
    assert response.status_code == 302 and response.headers["Location"].endswith("/")


def test_successful_order(customer_client, repositories, menu):
    fill_cart(customer_client)
    response = customer_client.post("/order/checkout", data=CHECKOUT)
    assert response.status_code == 302

    [order] = repositories.orders.list()
    assert order.customer_id == "kari"
    assert [(l.name, l.unit_price_nok, l.quantity) for l in order.lines] == [("Soup", 165, 20)]
    assert [(g.guest_count, g.note) for g in order.guest_groups] == [(2, "nut allergy")]
    assert order.event_date.isoformat() == EVENT
    assert response.headers["Location"].endswith(f"/account/orders/{order.id}")

    page = customer_client.get(f"/account/orders/{order.id}").get_data(as_text=True)
    assert order.reference in page
    assert "Submitted" in page and "Not paid" in page
    assert "nut allergy" in page
    assert customer_client.get("/cart").get_data(as_text=True).count("Your cart is empty") == 1


def test_errors_keep_input(customer_client, repositories, menu):
    fill_cart(customer_client)
    response = customer_client.post("/order/checkout", data={**CHECKOUT, "delivery_postcode": "50"})
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "Enter a 4-digit postcode." in html
    assert 'value="Bryggen 1"' in html
    assert 'value="nut allergy"' in html
    assert repositories.orders.list() == []


def test_other_customers_cannot_see_the_order(client, customer_client, repositories, menu):
    fill_cart(customer_client)
    customer_client.post("/order/checkout", data=CHECKOUT)
    [order] = repositories.orders.list()
    customer_client.post("/account/logout")

    add_user(repositories, "ola", "ola@example.test", Role.CUSTOMER)
    log_in(customer_client, "ola@example.test")
    assert customer_client.get(f"/account/orders/{order.id}").status_code == 404


def test_ordered_items_cannot_be_deleted(client, repositories, menu):
    add_user(repositories, "kari", "kari@example.test", Role.CUSTOMER)
    add_user(repositories, "admin", "admin@example.test", Role.ADMIN)
    log_in(client, "kari@example.test")
    fill_cart(client)
    client.post("/order/checkout", data=CHECKOUT)
    client.post("/account/logout")

    log_in(client, "admin@example.test")
    client.post("/admin/food-items/soup/delete")
    assert repositories.food_items.get("soup") is not None
    assert "has been ordered" in client.get("/admin/food-items/").get_data(as_text=True)
