import re

from app import create_app
from app.config import TestConfig
from app.models.domain import Allergen, EventCategory
from tests.conftest import make_item

VALID = {
    "name": "Rakfisk",
    "description": "Fermented trout",
    "price_nok": "220",
    "min_order_qty": "8",
    "event_categories": ["christmas_party"],
    "allergens": ["fish"],
    "published": "on",
}


def test_list_shows_all_items(admin_client, repositories):
    repositories.food_items.add(make_item("a", "Visible"))
    repositories.food_items.add(make_item("b", "Hidden draft", published=False))
    html = admin_client.get("/admin/food-items/").get_data(as_text=True)
    assert "Visible" in html and "Hidden draft" in html


def test_create_item(admin_client, repositories):
    assert admin_client.get("/admin/food-items/new").status_code == 200

    response = admin_client.post("/admin/food-items/new", data=VALID)
    assert response.status_code == 302

    [item] = repositories.food_items.list()
    assert item.name == "Rakfisk"
    assert item.price_nok == 220
    assert item.event_categories == [EventCategory.CHRISTMAS_PARTY]
    assert item.allergens == [Allergen.FISH]

    menu = admin_client.get("/").get_data(as_text=True)
    assert "Rakfisk" in menu


def test_invalid_create_keeps_input_and_shows_errors(admin_client, repositories):
    response = admin_client.post("/admin/food-items/new", data={**VALID, "price_nok": "abc", "name": ""})
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert 'value="abc"' in html
    assert "Name is required." in html
    assert "Price must be a whole number." in html
    assert repositories.food_items.list() == []


def test_edit_item(admin_client, repositories):
    repositories.food_items.add(make_item("a", "Fish soup", image_filename="soup.jpg"))
    assert "Fish soup" in admin_client.get("/admin/food-items/a/edit").get_data(as_text=True)

    response = admin_client.post("/admin/food-items/a/edit", data={**VALID, "name": "Better soup"})
    assert response.status_code == 302
    item = repositories.food_items.get("a")
    assert item.name == "Better soup"
    assert item.image_filename == "soup.jpg"  # pictures are kept (A2)


def test_edit_unknown_item_is_404(admin_client):
    assert admin_client.get("/admin/food-items/nope/edit").status_code == 404
    assert admin_client.post("/admin/food-items/nope/delete").status_code == 404


def test_publish_blocked_without_declared_allergens(admin_client, repositories):
    repositories.food_items.add(make_item("a", "Draft", published=False, allergens=[]))
    admin_client.post("/admin/food-items/a/publish")
    assert repositories.food_items.get("a").published is False
    html = admin_client.get("/admin/food-items/").get_data(as_text=True)
    assert "was not published" in html


def test_toggle_published(admin_client, repositories):
    repositories.food_items.add(make_item("a", "Soup", published=False))
    admin_client.post("/admin/food-items/a/publish")
    assert repositories.food_items.get("a").published is True
    admin_client.post("/admin/food-items/a/publish")
    assert repositories.food_items.get("a").published is False


def test_delete_item(admin_client, repositories):
    repositories.food_items.add(make_item("a", "Soup"))
    assert admin_client.post("/admin/food-items/a/delete").status_code == 302
    assert repositories.food_items.get("a") is None


def test_delete_requires_post(admin_client, repositories):
    repositories.food_items.add(make_item("a", "Soup"))
    assert admin_client.get("/admin/food-items/a/delete").status_code == 405


def test_csrf_token_required_when_enabled():
    config = TestConfig()
    config.WTF_CSRF_ENABLED = True
    app = create_app(config)
    client = app.test_client()

    assert client.post("/account/login", data={"email": "a@b.c", "password": "x"}).status_code == 400

    page = client.get("/account/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    response = client.post("/account/login", data={"email": "a@b.c", "password": "x", "csrf_token": token})
    assert response.status_code == 401  # passed CSRF, failed login
