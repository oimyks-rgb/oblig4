import pytest

from tests.conftest import make_item


@pytest.fixture
def menu(repositories):
    repositories.food_items.add(make_item("soup", "Soup", price_nok=165, min_order_qty=10))
    repositories.food_items.add(make_item("cake", "Cake", price_nok=1450, min_order_qty=1))
    repositories.food_items.add(make_item("hidden", "Hidden", published=False))


def cart_of(client):
    with client.session_transaction() as session:
        return dict(session.get("cart", {}))


def add(client, item_id, quantity=None):
    data = {"item_id": item_id} | ({"quantity": quantity} if quantity is not None else {})
    return client.post("/cart/add", data=data)


def test_menu_has_add_to_cart_with_minimum(client, menu):
    html = client.get("/").get_data(as_text=True)
    assert 'name="quantity" value="10" min="10"' in html


def test_add_defaults_to_minimum_and_adds_up(client, menu):
    add(client, "soup")
    assert cart_of(client) == {"soup": 10}
    add(client, "soup", "5")  # 5 more is fine, the total is 15
    assert cart_of(client) == {"soup": 15}
    assert "Cart (15)" in client.get("/").get_data(as_text=True)


def test_add_below_minimum_is_refused(client, menu):
    add(client, "soup", "9")
    assert cart_of(client) == {}
    assert "Minimum order for Soup is 10." in client.get("/").get_data(as_text=True)


def test_unpublished_or_unknown_items_cannot_be_added(client, menu):
    add(client, "hidden", "5")
    add(client, "nope", "5")
    assert cart_of(client) == {}


def test_cart_page_shows_lines_and_total(client, menu):
    add(client, "soup", "12")
    add(client, "cake", "2")
    html = client.get("/cart").get_data(as_text=True)
    assert "Soup" in html and "Cake" in html
    assert "kr 1 980" in html  # 12 x 165
    assert "kr 4 880" in html  # 1980 + 2900


def test_update_quantities(client, menu):
    add(client, "soup", "12")
    add(client, "cake", "2")
    response = client.post("/cart/update", data={"quantity-soup": "20", "quantity-cake": "0"})
    assert response.status_code == 302
    assert cart_of(client) == {"soup": 20}


def test_update_below_minimum_keeps_old_value(client, menu):
    add(client, "soup", "12")
    response = client.post("/cart/update", data={"quantity-soup": "3"})
    assert response.status_code == 400
    assert "Minimum order for Soup is 10." in response.get_data(as_text=True)
    assert cart_of(client) == {"soup": 12}


def test_remove(client, menu):
    add(client, "soup")
    client.post("/cart/remove", data={"item_id": "soup"})
    assert cart_of(client) == {}


def test_item_unpublished_after_adding_is_dropped(client, repositories, menu):
    add(client, "soup")
    repositories.food_items.update(make_item("soup", "Soup", min_order_qty=10, published=False))
    html = client.get("/cart").get_data(as_text=True)
    assert "no longer on the menu" in html
    assert cart_of(client) == {}
