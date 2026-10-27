from app.models.domain import EventCategory
from tests.conftest import make_item


def test_blueprints_registered(app):
    assert {"shop", "account", "admin"} <= set(app.blueprints)


def test_pages_load(client):
    for url in ("/", "/account/", "/admin/"):
        assert client.get(url).status_code == 200, url


def test_menu_shows_only_published_items_grouped_by_event(client, repositories):
    repositories.food_items.add(make_item("a", "Wedding cake", event_categories=[EventCategory.WEDDING]))
    repositories.food_items.add(make_item("b", "Secret dish", published=False))

    html = client.get("/").get_data(as_text=True)

    assert "Wedding cake" in html
    assert "Wedding</h2>" in html
    assert "Secret dish" not in html
    assert "Contains: Fish, Milk" in html
    assert "kr 165" in html


def test_admin_lists_unpublished_items(client, repositories):
    repositories.food_items.add(make_item("b", "Secret dish", published=False))
    assert "Secret dish" in client.get("/admin/").get_data(as_text=True)
