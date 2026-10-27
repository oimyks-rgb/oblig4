"""Neo4j implementations of the repository interfaces.

Graph model (see docs/models/graph-model.md):
  (:FoodItem)-[:CONTAINS]->(:Allergen {code})
  (:FoodItem)-[:SUITS]->(:EventCategory {code})
  (:User {id, email, name, passwordHash, role})
  (:User)-[:PLACED]->(:Order)-[:INCLUDES {quantity, unitPriceNok, name, position}]->(:FoodItem)
  (:Order)-[:HAS_GUEST_GROUP]->(:GuestGroup {guestCount, note, position})
  (:User)-[:ASKED]->(:Question {id, text, askedAt})-[:ABOUT]->(:Order)
  (:User)-[:WROTE]->(:Answer {text, answeredAt})-[:ANSWERS]->(:Question)
"""

from typing import Optional

from neo4j import Driver
from neo4j.exceptions import ConstraintError

from .domain import (
    Allergen,
    Answer,
    DietaryLabel,
    EventCategory,
    FoodItem,
    GuestGroup,
    Order,
    OrderLine,
    OrderStatus,
    PaymentStatus,
    Question,
    Role,
    User,
)
from .images import ImageStore
from .repositories import (
    DuplicateReference,
    FoodItemRepository,
    OrderRepository,
    QuestionRepository,
    Repositories,
    UserRepository,
)

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

    def is_ordered(self, item_id):
        records, _, _ = self._driver.execute_query(
            "RETURN EXISTS { (:Order)-[:INCLUDES]->(:FoodItem {id: $id}) } AS ordered", id=item_id
        )
        return records[0]["ordered"]


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


_ORDER_RETURN = """
CALL (o) {
  OPTIONAL MATCH (o)-[i:INCLUDES]->(f:FoodItem)
  WITH i, f ORDER BY i.position
  RETURN collect(i {.name, .unitPriceNok, .quantity, foodItemId: f.id}) AS lines
}
CALL (o) {
  OPTIONAL MATCH (o)-[:HAS_GUEST_GROUP]->(g:GuestGroup)
  WITH g ORDER BY g.position
  RETURN collect(g {.guestCount, .note}) AS groups
}
RETURN o, customerId, lines, groups
ORDER BY o.createdAt DESC
"""


def _native(value):
    """neo4j.time values -> Python date/datetime."""
    return value.to_native() if hasattr(value, "to_native") else value


def _to_order(record) -> Order:
    o = record["o"]
    return Order(
        id=o["id"],
        reference=o["reference"],
        customer_id=record["customerId"],
        created_at=_native(o["createdAt"]),
        event_date=_native(o["eventDate"]),
        guest_count=o["guestCount"],
        delivery_street=o["deliveryStreet"],
        delivery_postcode=o["deliveryPostcode"],
        delivery_city=o["deliveryCity"],
        lines=[
            OrderLine(line["foodItemId"], line["name"], line["unitPriceNok"], line["quantity"])
            for line in record["lines"]
        ],
        guest_groups=[GuestGroup(g["guestCount"], g["note"]) for g in record["groups"]],
        event_category=EventCategory(o["eventCategory"]) if o.get("eventCategory") else None,
        phone=o.get("phone", ""),
        comment=o.get("comment", ""),
        status=OrderStatus(o["status"]),
        payment_status=PaymentStatus(o["paymentStatus"]),
    )


class Neo4jOrderRepository(OrderRepository):
    def __init__(self, driver: Driver):
        self._driver = driver

    def add(self, order):
        taken, _, _ = self._driver.execute_query(
            "MATCH (o:Order {reference: $reference}) RETURN count(o) > 0 AS taken",
            reference=order.reference,
        )
        if taken[0]["taken"]:
            raise DuplicateReference(order.reference)
        try:
            records, _, _ = self._driver.execute_query(
                """
                MATCH (u:User {id: $customer_id})
                CREATE (u)-[:PLACED]->(o:Order)
                SET o = $props
                FOREACH (g IN $groups |
                  CREATE (o)-[:HAS_GUEST_GROUP]->(:GuestGroup {
                    guestCount: g.guestCount, note: g.note, position: g.position}))
                WITH o
                CALL (o) {
                  UNWIND $lines AS line
                  MATCH (f:FoodItem {id: line.foodItemId})
                  CREATE (o)-[:INCLUDES {quantity: line.quantity, unitPriceNok: line.unitPriceNok,
                                         name: line.name, position: line.position}]->(f)
                }
                RETURN o.id AS id
                """,
                customer_id=order.customer_id,
                props={
                    "id": order.id,
                    "reference": order.reference,
                    "createdAt": order.created_at,
                    "eventDate": order.event_date,
                    "eventCategory": order.event_category.value if order.event_category else None,
                    "guestCount": order.guest_count,
                    "deliveryStreet": order.delivery_street,
                    "deliveryPostcode": order.delivery_postcode,
                    "deliveryCity": order.delivery_city,
                    "phone": order.phone,
                    "comment": order.comment,
                    "status": order.status.value,
                    "paymentStatus": order.payment_status.value,
                },
                groups=[
                    {"guestCount": g.guest_count, "note": g.note, "position": n}
                    for n, g in enumerate(order.guest_groups)
                ],
                lines=[
                    {
                        "foodItemId": line.food_item_id,
                        "name": line.name,
                        "unitPriceNok": line.unit_price_nok,
                        "quantity": line.quantity,
                        "position": n,
                    }
                    for n, line in enumerate(order.lines)
                ],
            )
        except ConstraintError as error:
            raise DuplicateReference(order.reference) from error
        if not records:
            raise KeyError(f"Customer {order.customer_id} does not exist")
        return self.get(order.id)

    def _query(self, where: str, **params) -> list[Order]:
        records, _, _ = self._driver.execute_query(
            "MATCH (u:User)-[:PLACED]->(o:Order) " + where + " WITH o, u.id AS customerId " + _ORDER_RETURN,
            **params,
        )
        return [_to_order(r) for r in records]

    def get(self, order_id):
        orders = self._query("WHERE o.id = $id", id=order_id)
        return orders[0] if orders else None

    def list_for_customer(self, customer_id):
        return self._query("WHERE u.id = $customer_id", customer_id=customer_id)

    def list(self, status=None, event_date=None):
        return self._query(
            "WHERE ($status IS NULL OR o.status = $status) "
            "AND ($event_date IS NULL OR o.eventDate = $event_date)",
            status=status.value if status else None,
            event_date=event_date,
        )


_QUESTION_RETURN = """
OPTIONAL MATCH (staff:User)-[:WROTE]->(a:Answer)-[:ANSWERS]->(q)
RETURN q, customerId, orderId, a, staff.id AS staffId
ORDER BY q.askedAt
"""


def _to_question(record) -> Question:
    q, a = record["q"], record["a"]
    return Question(
        id=q["id"],
        order_id=record["orderId"],
        customer_id=record["customerId"],
        text=q["text"],
        asked_at=_native(q["askedAt"]),
        answer=Answer(a["text"], _native(a["answeredAt"]), record["staffId"]) if a else None,
    )


class Neo4jQuestionRepository(QuestionRepository):
    def __init__(self, driver: Driver):
        self._driver = driver

    def add(self, question):
        records, _, _ = self._driver.execute_query(
            """
            MATCH (u:User {id: $customer_id}), (o:Order {id: $order_id})
            CREATE (u)-[:ASKED]->(q:Question {id: $id, text: $text, askedAt: $asked_at})-[:ABOUT]->(o)
            RETURN q.id AS id
            """,
            customer_id=question.customer_id,
            order_id=question.order_id,
            id=question.id,
            text=question.text,
            asked_at=question.asked_at,
        )
        if not records:
            raise KeyError("Unknown customer or order")
        return self._get(question.id)

    def _query(self, where: str, **params) -> list[Question]:
        records, _, _ = self._driver.execute_query(
            "MATCH (u:User)-[:ASKED]->(q:Question)-[:ABOUT]->(o:Order) "
            + where
            + " WITH q, u.id AS customerId, o.id AS orderId "
            + _QUESTION_RETURN,
            **params,
        )
        return [_to_question(r) for r in records]

    def _get(self, question_id):
        found = self._query("WHERE q.id = $id", id=question_id)
        return found[0] if found else None

    def list_for_order(self, order_id):
        return self._query("WHERE o.id = $order_id", order_id=order_id)

    def list_for_customer(self, customer_id):
        return self._query("WHERE u.id = $customer_id", customer_id=customer_id)

    def answer(self, question_id, answer):
        records, _, _ = self._driver.execute_query(
            """
            MATCH (q:Question {id: $id})
            OPTIONAL MATCH (old:Answer)-[:ANSWERS]->(q)
            DETACH DELETE old
            WITH DISTINCT q
            MATCH (staff:User {id: $staff_id})
            CREATE (staff)-[:WROTE]->(:Answer {text: $text, answeredAt: $answered_at})-[:ANSWERS]->(q)
            RETURN q.id AS id
            """,
            id=question_id,
            staff_id=answer.answered_by_id,
            text=answer.text,
            answered_at=answer.answered_at,
        )
        if not records:
            raise KeyError(question_id)
        return self._get(question_id)

    def list_unanswered(self):
        return self._query("WHERE NOT EXISTS { (:Answer)-[:ANSWERS]->(q) }")


def neo4j_repositories(driver: Driver, images: ImageStore) -> Repositories:
    return Repositories(
        food_items=Neo4jFoodItemRepository(driver),
        users=Neo4jUserRepository(driver),
        images=images,
        orders=Neo4jOrderRepository(driver),
        questions=Neo4jQuestionRepository(driver),
    )
