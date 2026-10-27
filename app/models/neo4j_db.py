"""Neo4j connection, schema and reference data.

Only the model layer imports this module.
"""

import atexit

from neo4j import Driver, GraphDatabase, NotificationDisabledClassification

from .domain import Allergen, EventCategory

_CONSTRAINTS = [
    "CREATE CONSTRAINT food_item_id IF NOT EXISTS FOR (f:FoodItem) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
    "CREATE CONSTRAINT user_email IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
    "CREATE CONSTRAINT allergen_code IF NOT EXISTS FOR (a:Allergen) REQUIRE a.code IS UNIQUE",
    "CREATE CONSTRAINT event_category_code IF NOT EXISTS "
    "FOR (c:EventCategory) REQUIRE c.code IS UNIQUE",
    "CREATE CONSTRAINT order_id IF NOT EXISTS FOR (o:Order) REQUIRE o.id IS UNIQUE",
    "CREATE CONSTRAINT order_reference IF NOT EXISTS FOR (o:Order) REQUIRE o.reference IS UNIQUE",
    "CREATE CONSTRAINT question_id IF NOT EXISTS FOR (q:Question) REQUIRE q.id IS UNIQUE",
]


def create_driver(uri: str, user: str, password: str) -> Driver:
    """Create a driver. It connects lazily, on the first query, and is closed at exit."""
    if not (uri and user and password):
        raise RuntimeError(
            "Neo4j is not configured. Copy .env.example to .env and set "
            "NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD."
        )
    driver = GraphDatabase.driver(
        uri,
        auth=(user, password),
        # "label/relationship type does not exist" is expected on an empty database
        notifications_disabled_classifications=[NotificationDisabledClassification.UNRECOGNIZED],
    )
    atexit.register(driver.close)
    return driver


def ensure_schema(driver: Driver) -> None:
    """Create constraints and the Allergen / EventCategory reference nodes. Safe to rerun."""
    for statement in _CONSTRAINTS:
        driver.execute_query(statement)
    driver.execute_query(
        """
        UNWIND $allergens AS a
        MERGE (n:Allergen {code: a.code}) SET n.name = a.name
        """,
        allergens=[{"code": a.value, "name": a.label} for a in Allergen],
    )
    driver.execute_query(
        """
        UNWIND $categories AS c
        MERGE (n:EventCategory {code: c.code}) SET n.name = c.name
        """,
        categories=[{"code": c.value, "name": c.label} for c in EventCategory],
    )


def reset_database(driver: Driver) -> None:
    """Delete every node and relationship. Used only by `seed.py --reset`."""
    # CALL ... IN TRANSACTIONS needs an auto-commit transaction, so use session.run
    with driver.session() as session:
        session.run(
            "MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 1000 ROWS"
        ).consume()
