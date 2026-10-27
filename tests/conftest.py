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


TEST_PASSWORD = "correct horse battery staple"


def add_user(repositories, user_id, email, role):
    from werkzeug.security import generate_password_hash

    from app.models.domain import User

    return repositories.users.add(User(user_id, email, user_id.title(), generate_password_hash(TEST_PASSWORD), role))


def log_in(client, email, password=TEST_PASSWORD, **extra):
    return client.post("/account/login", data={"email": email, "password": password, **extra})


@pytest.fixture
def admin_client(client, repositories):
    from app.models.domain import Role

    add_user(repositories, "admin", "admin@example.test", Role.ADMIN)
    log_in(client, "admin@example.test")
    return client


@pytest.fixture
def customer_client(client, repositories):
    from app.models.domain import Role

    add_user(repositories, "kari", "kari@example.test", Role.CUSTOMER)
    log_in(client, "kari@example.test")
    return client
