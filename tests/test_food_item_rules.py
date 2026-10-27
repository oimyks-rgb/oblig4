from werkzeug.datastructures import MultiDict

from app.models.domain import Allergen, DietaryLabel, EventCategory
from app.models.food_items import parse_food_item, publish_errors


def form(**overrides):
    data = {
        "name": "Fish soup",
        "description": "Creamy",
        "price_nok": "165",
        "min_order_qty": "10",
        "event_categories": ["conference"],
        "allergens": ["fish", "milk"],
        "published": "on",
    }
    data.update(overrides)
    return MultiDict([(k, v) for k, vs in data.items() for v in (vs if isinstance(vs, list) else [vs])])


def test_valid_form_gives_food_item():
    item, errors = parse_food_item(form(), item_id="x")
    assert errors == {}
    assert item.id == "x"
    assert item.name == "Fish soup"
    assert item.price_nok == 165
    assert item.min_order_qty == 10
    assert item.event_categories == [EventCategory.CONFERENCE]
    assert item.allergens == [Allergen.FISH, Allergen.MILK]
    assert item.published is True


def test_new_items_get_an_id():
    item, _ = parse_food_item(form())
    assert len(item.id) == 32


def test_values_are_kept_in_enum_order():
    item, _ = parse_food_item(form(allergens=["milk", "fish"]))
    assert item.allergens == [Allergen.FISH, Allergen.MILK]


def test_name_is_required_and_limited():
    assert "name" in parse_food_item(form(name="  "))[1]
    assert "name" in parse_food_item(form(name="x" * 101))[1]


def test_description_is_limited():
    assert "description" in parse_food_item(form(description="x" * 1001))[1]


def test_price_and_minimum_must_be_positive_whole_numbers():
    for bad in ("", "abc", "12.5", "0", "-3"):
        errors = parse_food_item(form(price_nok=bad, min_order_qty=bad))[1]
        assert "price_nok" in errors, bad
        assert "min_order_qty" in errors, bad


def test_unknown_codes_are_rejected():
    assert "allergens" in parse_food_item(form(allergens=["fish", "plutonium"]))[1]
    assert "event_categories" in parse_food_item(form(event_categories=["funeral"]))[1]


def test_publishing_requires_event_category():
    assert "event_categories" in parse_food_item(form(event_categories=[]))[1]
    assert "event_categories" not in parse_food_item(form(event_categories=[], published=""))[1]


def test_publishing_requires_declared_allergens():
    errors = parse_food_item(form(allergens=[]))[1]
    assert "allergens" in errors

    item, errors = parse_food_item(form(allergens=[], no_allergens="on"))
    assert errors == {}
    assert item.no_allergens is True

    # Saving as a hidden draft without allergens is allowed
    assert parse_food_item(form(allergens=[], published=""))[1] == {}


def test_allergens_and_none_cannot_both_be_chosen():
    assert "allergens" in parse_food_item(form(no_allergens="on"))[1]


def test_gluten_free_item_cannot_contain_gluten():
    errors = parse_food_item(form(allergens=["gluten"], dietary_labels=["gluten_free"]))[1]
    assert "dietary_labels" in errors
    item, errors = parse_food_item(form(allergens=["milk"], dietary_labels=["gluten_free"]))
    assert errors == {}
    assert item.dietary_labels == [DietaryLabel.GLUTEN_FREE]


def test_publish_errors_for_stored_item():
    item, _ = parse_food_item(form(allergens=[], event_categories=[], published=""))
    assert set(publish_errors(item)) == {"allergens", "event_categories"}
