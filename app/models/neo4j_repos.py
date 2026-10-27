"""Neo4j implementations of the repository interfaces.

Graph model (see docs/models/graph-model.md):
  (:FoodItem)-[:CONTAINS]->(:Allergen {code})
  (:FoodItem)-[:SUITS]->(:EventCategory {code})
  (:User {id, email, name, passwordHash, role})
"""

from typing import Optional

from neo4j import Driver

from .domain import Allergen, DietaryLabel, EventCategory, FoodItem, Role, User
from .repositories import FoodItemRepository, Repositories, UserRepository

_FOOD_ITEM_RETURN = """
OPTIONAL MATCH (f)-[:CONTAINS]->(a:Allergen)
WITH f, collect(DISTINCT a.code) AS allergens
OPTIONAL MATCH (f)-[:SUITS]->(c:EventCategory)
RETURN f, allergens, collect(DISTINCT c.code) AS categories
ORDER BY toLower(f.name)
"""

_SET_FOOD_ITEM_RELATIONSHIPS = """
FOREACH (code IN $allergens |
  MERGE (a:Allergen {code: code}) MERGE (f)-[:CONTAINS]->(a))
FOREACH (code IN $categories |
  MERGE (c:EventCategory {code: code}) MERGE (f)-[:SUITS]->(c))
"""


def _food_item_params(item: FoodItem) -> dict:
    return {
        "id": item.id,
        "props": {
            "name": item.name,
            "description": item.description,
            "priceNok": item.price_nok,
            "minOrderQty": item.min_order_qty,
            "dietaryLabels": [d.value for d in item.dietary_labels],
            "published": item.published,
            "noAllergens": item.no_allergens,
            "imageFilename": item.image_filename,
        },
        "allergens": [a.value for a in item.allergens],
        "categories": [c.value for c in item.event_categories],
    }


def _in_enum_order(enum, codes):
    wanted = set(codes)
    return [member for member in enum if member.value in wanted]


def _to_food_item(record) -> FoodItem:
    f = record["f"]
    return FoodItem(
        id=f["id"],
        name=f["name"],
        description=f.get("description", ""),
        price_nok=f["priceNok"],
        min_order_qty=f["minOrderQty"],
        event_categories=_in_enum_order(EventCategory, record["categories"]),
        allergens=_in_enum_order(Allergen, record["allergens"]),
        dietary_labels=[DietaryLabel(d) for d in f.get("dietaryLabels", [])],
        published=f.get("published", False),
        no_allergens=f.get("noAllergens", False),
        image_filename=f.get("imageFilename"),
    )


class Neo4jFoodItemRepository(FoodItemRepository):
    def __init__(self, driver: Driver):
        self._driver = driver

    def list(self, published_only=False, category: Optional[EventCategory] = None):
        records, _, _ = self._driver.execute_query(
            """
            MATCH (f:FoodItem)
            WHERE ($published_only = false OR f.published = true)
              AND ($category IS NULL
                   OR EXISTS { (f)-[:SUITS]->(:EventCategory {code: $category}) })
            """
            + _FOOD_ITEM_RETURN,
            published_only=published_only,
            category=category.value if category else None,
        )
        return [_to_food_item(r) for r in records]

    def get(self, item_id):
        records, _, _ = self._driver.execute_query(
            "MATCH (f:FoodItem {id: $id})" + _FOOD_ITEM_RETURN, id=item_id
        )
        return _to_food_item(records[0]) if records else None

    def add(self, item):
        if self.get(item.id):
            raise ValueError(f"Food item {item.id} already exists")
        self._driver.execute_query(
            "CREATE (f:FoodItem {id: $id}) SET f += $props WITH f"
            + _SET_FOOD_ITEM_RELATIONSHIPS,
            _food_item_params(item),
        )
        return self.get(item.id)

    def update(self, item):
        records, _, _ = self._driver.execute_query(
            """
            MATCH (f:FoodItem {id: $id})
            SET f += $props
            WITH f
            OPTIONAL MATCH (f)-[r:CONTAINS|SUITS]->()
            DELETE r
            WITH DISTINCT f
            """
            + _SET_FOOD_ITEM_RELATIONSHIPS
            + "RETURN f.id AS id",
            _food_item_params(item),
        )
        if not records:
            raise KeyError(item.id)
        return self.get(item.id)

    def delete(self, item_id):
        records, _, _ = self._driver.execute_query(
            "MATCH (f:FoodItem {id: $id}) DETACH DELETE f RETURN count(*) AS deleted",
            id=item_id,
        )
        return bool(records) and records[0]["deleted"] > 0


def _to_user(record) -> User:
    u = record["u"]
    return User(
        id=u["id"],
        email=u["email"],
        name=u["name"],
        password_hash=u["passwordHash"],
        role=Role(u["role"]),
    )


class Neo4jUserRepository(UserRepository):
    def __init__(self, driver: Driver):
        self._driver = driver

    def get(self, user_id):
        records, _, _ = self._driver.execute_query(
            "MATCH (u:User {id: $id}) RETURN u", id=user_id
        )
        return _to_user(records[0]) if records else None

    def get_by_email(self, email):
        records, _, _ = self._driver.execute_query(
            "MATCH (u:User {email: $email}) RETURN u", email=email.strip().lower()
        )
        return _to_user(records[0]) if records else None

    def add(self, user):
        if self.get_by_email(user.email):
            raise ValueError(f"E-mail {user.email} is already registered")
        self._driver.execute_query(
            """
            CREATE (u:User {id: $id, email: $email, name: $name,
                            passwordHash: $password_hash, role: $role})
            """,
            id=user.id,
            email=user.email.strip().lower(),
            name=user.name,
            password_hash=user.password_hash,
            role=user.role.value,
        )
        return self.get(user.id)


def neo4j_repositories(driver: Driver) -> Repositories:
    return Repositories(
        food_items=Neo4jFoodItemRepository(driver), users=Neo4jUserRepository(driver)
    )
