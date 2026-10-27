"""Seed the Neo4j database in .env with synthetic data.

    python seed.py           add or update sample data (safe to rerun)
    python seed.py --reset   delete EVERYTHING in the database first (asks for confirmation)

The whole group shares one database: agree before using --reset.
"""

import argparse
import os
import sys

from werkzeug.security import generate_password_hash

from app import create_app
from app.models import repos
from app.models.domain import Allergen as A
from app.models.domain import DietaryLabel as D
from app.models.domain import EventCategory as E
from app.models.domain import FoodItem, Role, User
from app.models.neo4j_db import create_driver, ensure_schema, reset_database

FOOD_ITEMS = [
    FoodItem("seed-kransekake", "Kransekake", "Almond ring cake, 18 rings, decorated with flags.",
             1450, 1, [E.WEDDING, E.CONFIRMATION, E.BIRTHDAY], [A.NUTS, A.EGGS], [D.GLUTEN_FREE], True),
    FoodItem("seed-smorbrod", "Smørbrød platter", "Open sandwiches with shrimp, roast beef and egg.",
             95, 10, [E.CONFIRMATION, E.BIRTHDAY, E.LUNCH_MEETING], [A.GLUTEN, A.CRUSTACEANS, A.EGGS, A.MILK, A.MUSTARD], [], True),
    FoodItem("seed-fiskesuppe", "Bergen fish soup", "Creamy fish soup with root vegetables and fresh herbs.",
             165, 15, [E.CONFERENCE, E.LUNCH_MEETING, E.WEDDING], [A.FISH, A.MILK, A.CELERY], [D.GLUTEN_FREE], True),
    FoodItem("seed-pinnekjott", "Pinnekjøtt", "Salted, dried lamb ribs with mashed swede and potatoes.",
             395, 20, [E.CHRISTMAS_PARTY], [A.MILK], [D.GLUTEN_FREE], True),
    FoodItem("seed-ribbe", "Ribbe", "Roast pork belly with crackling, medisterkaker and red cabbage.",
             375, 20, [E.CHRISTMAS_PARTY], [A.GLUTEN, A.MILK, A.EGGS], [], True),
    FoodItem("seed-laks", "Baked salmon", "Oven-baked salmon with lemon, dill sauce and new potatoes.",
             285, 15, [E.WEDDING, E.CONFIRMATION, E.CONFERENCE], [A.FISH, A.MILK], [D.GLUTEN_FREE], True),
    FoodItem("seed-veggie-lasagne", "Vegetable lasagne", "Lasagne with lentils, spinach and ricotta.",
             210, 10, [E.BIRTHDAY, E.CONFERENCE, E.LUNCH_MEETING], [A.GLUTEN, A.MILK, A.EGGS], [D.VEGETARIAN], True),
    FoodItem("seed-falafel", "Falafel bowl", "Falafel, hummus, pickled vegetables and herb salad.",
             155, 10, [E.CONFERENCE, E.LUNCH_MEETING, E.BIRTHDAY], [A.SESAME], [D.VEGAN, D.LACTOSE_FREE, D.HALAL], True),
    FoodItem("seed-baguette", "Baguette tray", "Half baguettes with ham, cheese and chicken pesto.",
             89, 12, [E.CONFERENCE, E.LUNCH_MEETING], [A.GLUTEN, A.MILK, A.NUTS], [], True),
    FoodItem("seed-bryllupskake", "Wedding cake", "Three-tier sponge cake with cream and berries, 40 portions.",
             3900, 1, [E.WEDDING], [A.GLUTEN, A.EGGS, A.MILK], [D.VEGETARIAN], True),
    FoodItem("seed-multekrem", "Cloudberry cream", "Whipped cream with cloudberries. Seasonal, not yet on sale.",
             75, 20, [E.CHRISTMAS_PARTY, E.WEDDING], [A.MILK], [D.GLUTEN_FREE, D.VEGETARIAN], False),
]

USERS = [
    # (id, email, name, role, password env var)
    ("seed-admin", "admin@ektemat.test", "Ekte Mat Admin", Role.ADMIN, "SEED_ADMIN_PASSWORD"),
    ("seed-kari", "kari.nordmann@ektemat.test", "Kari Nordmann", Role.CUSTOMER, "SEED_CUSTOMER_PASSWORD"),
    ("seed-ola", "ola.hansen@ektemat.test", "Ola Hansen", Role.CUSTOMER, "SEED_CUSTOMER_PASSWORD"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="delete all data before seeding")
    args = parser.parse_args()

    app = create_app()  # loads .env
    missing = [v for v in ("SEED_ADMIN_PASSWORD", "SEED_CUSTOMER_PASSWORD") if not os.environ.get(v)]
    if missing:
        print(f"Set {', '.join(missing)} in .env first.", file=sys.stderr)
        return 1

    driver = create_driver(app.config["NEO4J_URI"], app.config["NEO4J_USER"], app.config["NEO4J_PASSWORD"])
    if args.reset:
        answer = input("This deletes ALL data in the shared database. Type 'reset' to continue: ")
        if answer.strip() != "reset":
            print("Aborted.")
            return 1
        reset_database(driver)
        print("Database cleared.")

    ensure_schema(driver)

    with app.app_context():
        food_items = repos().food_items
        for item in FOOD_ITEMS:
            if food_items.get(item.id):
                food_items.update(item)
            else:
                food_items.add(item)

        users = repos().users
        for user_id, email, name, role, password_var in USERS:
            if not users.get_by_email(email):
                users.add(User(user_id, email, name, generate_password_hash(os.environ[password_var]), role))

    print(f"Seeded {len(FOOD_ITEMS)} food items and {len(USERS)} users.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
