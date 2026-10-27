"""C1 Menu by event: cards grouped by kind of event with picture, price, minimum order and allergens."""

import re

import pytest

from app.models.domain import Allergen, DietaryLabel, EventCategory as E
from app.models.images import process_image
from tests.conftest import make_item, picture_bytes


@pytest.fixture
def menu(repositories):
    picture = repositories.images.save(process_image(picture_bytes()))
    repositories.food_items.add(make_item(
        "soup", "Fish soup", price_nok=165, min_order_qty=10,
        event_categories=[E.CONFERENCE, E.WEDDING], image_filename=picture,
        dietary_labels=[DietaryLabel.GLUTEN_FREE],
    ))
    repositories.food_items.add(make_item(
        "cake", "Wedding cake", price_nok=3900, min_order_qty=1,
        event_categories=[E.WEDDING], allergens=[], no_allergens=True,
    ))
    repositories.food_items.add(make_item("secret", "Secret dish", published=False, event_categories=[E.BIRTHDAY]))
    return picture


def html(client, url="/"):
    response = client.get(url)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def section(page, code):
    match = re.search(rf'<section class="category" id="event-{code}">(.*?)</section>', page, re.S)
    return match.group(1) if match else None


def card(page, name):
    """The <article> of the card with this name."""
    return next(a for a in re.findall(r'<article class="card">.*?</article>', page, re.S) if f"<h3>{name}</h3>" in a)


def test_sections_follow_event_order_and_skip_empty_ones(client, menu):
    page = html(client)
    assert re.findall(r"<h2>(.*?)</h2>", page) == ["Wedding", "Conference"]
    assert section(page, "birthday") is None  # only an unpublished item
    assert "Secret dish" not in page


def test_item_appears_under_every_event_it_suits(client, menu):
    page = html(client)
    assert "Fish soup" in section(page, "wedding")
    assert "Fish soup" in section(page, "conference")
    assert "Wedding cake" not in section(page, "conference")


def test_card_shows_picture_price_minimum_and_allergens(client, menu):
    soup = card(html(client), "Fish soup")
    assert f'src="/images/{menu}"' in soup
    assert "kr 165" in soup
    assert "Minimum order: 10 portions" in soup
    assert "Contains: Fish, Milk" in soup
    assert "Gluten-free" in soup


def test_card_without_picture_uses_placeholder_and_shows_no_allergens(client, menu):
    cake = card(html(client), "Wedding cake")
    assert "img/placeholder.svg" in cake
    assert "Minimum order: 1 portion<" in cake
    assert "No allergens" in cake


def test_event_navigation_lists_events_with_items(client, menu):
    page = html(client)
    nav = re.search(r'<nav class="event-nav".*?</nav>', page, re.S).group(0)
    assert re.findall(r">([^<]+)</a>", nav) == ["All events", "Wedding", "Conference"]
    assert 'aria-current="page">All events' in nav


def test_filter_by_event(client, menu):
    page = html(client, "/?event=conference")
    assert re.findall(r"<h2>(.*?)</h2>", page) == ["Conference"]
    assert "Wedding cake" not in page
    assert 'href="/?event=conference" aria-current="page"' in page


def test_unknown_event_shows_whole_menu(client, menu):
    page = html(client, "/?event=funeral")
    assert "Unknown event type; showing the whole menu." in page
    assert re.findall(r"<h2>(.*?)</h2>", page) == ["Wedding", "Conference"]


def test_event_without_items(client, menu):
    page = html(client, "/?event=birthday")
    assert "Nothing on the menu for this kind of event yet." in page


def test_empty_menu(client):
    assert "No food items are published yet." in html(client)
