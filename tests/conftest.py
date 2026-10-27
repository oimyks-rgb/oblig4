import pytest

from app import create_app
from app.config import TestConfig
from app.models.domain import Allergen, EventCategory, FoodItem


@pytest.fixture
def app():
    return create_app(TestConfig())


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def repositories(app):
    return app.extensions["repos"]


def make_item(item_id="item-1", name="Fish soup", published=True, **kwargs) -> FoodItem:
    defaults = dict(
        description="Soup",
        price_nok=165,
        min_order_qty=10,
        event_categories=[EventCategory.CONFERENCE],
        allergens=[Allergen.FISH, Allergen.MILK],
    )
    defaults.update(kwargs)
    return FoodItem(id=item_id, name=name, published=published, **defaults)
