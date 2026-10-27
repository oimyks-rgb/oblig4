"""Repository contract tests against the shared Neo4j database in .env.

Run with: pytest -m neo4j
Test data uses ids starting with "test-" and e-mails ending with "@test.invalid",
and only that data is deleted afterwards.
"""

import os

import pytest
from dotenv import load_dotenv

from tests.test_memory_repos import check_food_item_repository, check_user_repository

pytestmark = pytest.mark.neo4j

load_dotenv()


@pytest.fixture(scope="module")
def driver():
    if not os.environ.get("NEO4J_URI"):
        pytest.skip("NEO4J_URI is not set")
    from app.models.neo4j_db import create_driver, ensure_schema

    driver = create_driver(
        os.environ["NEO4J_URI"], os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]
    )
    ensure_schema(driver)
    yield driver
    driver.close()


@pytest.fixture(autouse=True)
def cleanup(driver):
    yield
    driver.execute_query(
        "MATCH (q:Question) WHERE q.id STARTS WITH 'test-' "
        "OPTIONAL MATCH (a:Answer)-[:ANSWERS]->(q) DETACH DELETE q, a"
    )
    driver.execute_query(
        "MATCH (o:Order) WHERE o.id STARTS WITH 'test-' "
        "OPTIONAL MATCH (o)-[:HAS_GUEST_GROUP]->(g:GuestGroup) DETACH DELETE o, g"
    )
    driver.execute_query("MATCH (f:FoodItem) WHERE f.id STARTS WITH 'test-' DETACH DELETE f")
    driver.execute_query("MATCH (u:User) WHERE u.email ENDS WITH '@test.invalid' DETACH DELETE u")


def test_neo4j_food_item_repository(driver):
    from app.models.neo4j_repos import Neo4jFoodItemRepository

    check_food_item_repository(Neo4jFoodItemRepository(driver), prefix="test-")


def test_neo4j_user_repository(driver):
    from app.models.neo4j_repos import Neo4jUserRepository

    check_user_repository(Neo4jUserRepository(driver), suffix="@test.invalid", prefix="test-")


def test_cleanup_leaves_no_test_data(driver):
    records, _, _ = driver.execute_query(
        "MATCH (f:FoodItem) WHERE f.id STARTS WITH 'test-' RETURN count(f) AS n"
    )
    assert records[0]["n"] == 0


def test_neo4j_order_repository(driver):
    from app.models.memory import MemoryImageStore
    from app.models.neo4j_repos import neo4j_repositories
    from tests.test_order_repository import check_order_repository

    check_order_repository(
        neo4j_repositories(driver, MemoryImageStore()), prefix="test-", email_suffix="@test.invalid"
    )


def test_neo4j_question_repository(driver):
    from app.models.memory import MemoryImageStore
    from app.models.neo4j_repos import neo4j_repositories
    from tests.test_question_repository import check_question_repository

    check_question_repository(
        neo4j_repositories(driver, MemoryImageStore()), prefix="test-", email_suffix="@test.invalid"
    )
