# Ekte Mat Online

A catering web shop for Ekte Mat AS, a fictional catering company in Bergen. Built for INFO212 obligatory assignment 4.
It has two parts:
- **Customer site:** menu by event type, cart, order form, my orders, questions about an order.
- **Admin panel:** food items, images, orders (order status and payment status), answering questions.

All data is synthetic. Never add real personal data.

## Requirements and models

- Assignment minimum: A1–A4 (admin) and C1–C5 (customer). These take precedence over the lab backlog when they conflict.
- Backlog: `docs/requirements/backlog.md` (user stories US-xx, NFR-xx, conflicts Cxx). It is exported from `EkteMat_backlog_v2.xlsx`, which is the source of truth.
- Models: `docs/models/` (domain class diagram, order state machine, use cases, BPMN).
- Known differences from the lab models:
  - Order status follows the assignment: `submitted → approved → in_preparation → delivered`, plus `rejected` and `cancelled`.
  - Payment status is a separate field: `not_paid`, `deposit_paid`, `invoiced`, `paid`.
  - The lab model's `Menu`/`Dish` becomes `FoodItem`, which has a minimum order quantity, event categories, allergens, dietary labels and a published flag.

## Architecture (MVC, Flask)

Planned layout. Update this section when the code exists.

```
app/
  __init__.py      # create_app() factory, registers blueprints
  models/          # domain classes + Neo4j repositories (the ONLY code that touches the database)
  controllers/     # Flask blueprints: shop, account, admin
  templates/       # Jinja2 views, one folder per blueprint
  static/          # CSS, JS, uploaded images
tests/             # in-memory fake repositories; Neo4j tests marked `neo4j`
seed.py            # synthetic food items, an admin, test customers
.env.example       # names of the settings, no values
```

Layer rules:
- Controllers call repository classes only. They never import the `neo4j` driver or write Cypher.
- Views get plain data from controllers and contain no business logic.
- Repositories return domain objects, not driver records. Use parameterised Cypher (`$param`), never string formatting.
- Storage is a shared Neo4j AuraDB Free instance, used through the official `neo4j` Python driver. This also covers assignment 5: say "Neo4j: yes" on the report's front page.
- Graph model: nodes are labelled like the domain classes (`:FoodItem`, `:Customer`, `:Order`, ...). Relationships are UPPER_SNAKE verbs (for example `(:Customer)-[:PLACED]->(:Order)-[:CONTAINS {quantity}]->(:FoodItem)`). Document the graph model in `docs/models/` when it changes.
- Connection settings come from `.env`: `NEO4J_URI` (`neo4j+s://<id>.databases.neo4j.io`), `NEO4J_USER`, `NEO4J_PASSWORD`. Share them within the group privately, never in git, issues or chat logs.
- Each repository has an interface (an abstract base class) with a Neo4j implementation and an in-memory fake used in tests.

## Running and testing

Planned commands. Keep these in sync with the README.

```
cp .env.example .env          # then fill in the Aura credentials
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py                # creates constraints and sample data with MERGE (safe to rerun)
flask --app app run --debug
pytest                        # fast tests, in-memory repositories, no database
pytest -m neo4j               # repository tests against Aura
```

The whole group shares one Aura database:
- `seed.py` must never delete data unless it is run with `--reset`. Agree in the group before resetting.
- Neo4j tests only create nodes with the extra label `:Test`, and delete only `:Test` nodes afterwards.
- Aura Free pauses after a few days without use. Resume it in the Aura console if the connection fails.

## Team rules

- Plan every larger feature in plan mode first, and commit the agreed plan to `docs/plans/<yyyy-mm-dd>-<feature>.md` before building it.
- Work on a feature branch and merge to `main` through a pull request. Every group member commits.
- Reference the requirement in commits and PRs where it applies (for example "C2: reject quantities below minimum").
- Add or update tests with every feature, and run `pytest` before committing.
- Secrets go in `.env`, which git ignores. Never commit an API key (for example the Claude or image-service key for A2).
- Keep this file short and true. Update it when the layout or commands change.
