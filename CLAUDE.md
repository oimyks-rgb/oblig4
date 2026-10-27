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

```
app/
  __init__.py        # create_app(config): loads .env, builds repositories, registers blueprints
  config.py          # Config (Neo4j from .env), TestConfig (in-memory)
  models/            # the ONLY layer that touches the database
    domain.py        # dataclasses + enums (FoodItem, User, OrderStatus, ...)
    repositories.py  # repository interfaces (ABCs) + Repositories container
    neo4j_db.py      # driver, ensure_schema(), reset_database()
    neo4j_repos.py   # Neo4j implementations (Cypher lives here only)
    memory.py        # in-memory implementations for tests
    food_items.py    # business rules: parse_food_item(), publish_errors()
    accounts.py      # authenticate()
    cart.py          # cart rules: validate_quantity(), cart_lines() (cart = session dict)
    orders.py        # parse_checkout(), place_order(), MIN_LEAD_DAYS
    images.py        # process_image(), ImageStore (content-hash names), LocalImageStore
    image_generation.py  # ImageGenerator: GeminiImageGenerator, FakeImageGenerator, prompts
  controllers/       # blueprints: shop (/ and /cart), account (/account), order (/order), admin (/admin)
    auth.py          # g.user, current_user in templates, @login_required, @admin_required
  templates/         # Jinja2 views, one folder per blueprint; base.html
  static/            # css/, img/, uploads/ (git-ignored)
tests/               # pytest; test_neo4j_repos.py is marked `neo4j`
seed.py              # synthetic food items, an admin, test customers, seed pictures
generate_images.py   # makes seed_images/*.jpg with the configured image generator (paid for Gemini)
seed_images/         # committed default illustrations for the seed items
docs/models/graph-model.md  # the graph data model
```

Layer rules:
- Controllers get data through `repos()` from `app.models` (for example `repos().food_items.list(published_only=True)`). They never import `neo4j` or write Cypher.
- Views get plain data from controllers and contain no business logic.
- Validation and business rules live in the model layer (pattern: `models/food_items.py` returns the object plus a field -> message dict). Controllers only pass `request.form` in and re-render with the errors (status 400).
- Pictures go through `repos().images` (an `ImageStore`, files in `instance/images/`), and AI pictures through `image_generator()` (None when `IMAGE_GENERATOR` is empty). New pictures are always saved as a draft and previewed before they replace the current one (A2).
- The cart is `session["cart"]` (`{food_item_id: quantity}`); login and registration keep it. The minimum order applies to the total quantity of an item.
- Orders copy the item name and price into each line. Ordered food items can't be deleted (`is_ordered`). Guest groups hold a count and a note, never guest names (US-36).
- Tests never call Gemini: use `FakeImageGenerator` or a fake client. `GEMINI_API_KEY` lives only in `.env`.
- Every admin route has `@admin_required`. Every POST form includes `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` (Flask-WTF `CSRFProtect`). State changes are POST, never GET.
- A new kind of data needs a domain class, an interface in `repositories.py`, and both a Neo4j and an in-memory implementation. Check both with one shared contract test (see `tests/test_memory_repos.py`).
- Repositories return domain objects, not driver records. Use parameterised Cypher (`$param`), never string formatting.
- Storage is a shared Neo4j AuraDB Free instance, used through the official `neo4j` Python driver. This also covers assignment 5: say "Neo4j: yes" on the report's front page.
- Graph model: nodes are labelled like the domain classes, and relationships are UPPER_SNAKE verbs. Update `docs/models/graph-model.md` when the model changes.
- Other `.env` settings: `IMAGE_GENERATOR` (gemini/fake/empty), `GEMINI_API_KEY`, `GEMINI_IMAGE_MODEL`.
- Connection settings come from `.env`: `NEO4J_URI` (`neo4j+s://<id>.databases.neo4j.io`), `NEO4J_USER`, `NEO4J_PASSWORD`. Share them within the group privately, never in git, issues or chat logs.

## Running and testing

Keep these commands in sync with the README.

```
cp .env.example .env          # then fill in the Aura credentials and seed passwords
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py                # constraints + sample data, safe to rerun
flask --app app run --debug --port 5001   # port 5000 is AirPlay on macOS
pytest                        # fast tests, in-memory repositories, no database
pytest -m neo4j               # repository tests against Aura
```

The whole group shares one Aura database:
- `seed.py` must never delete data unless it is run with `--reset`, which asks for confirmation. Agree in the group before resetting.
- Neo4j tests only create data with ids starting `test-` and e-mails ending `@test.invalid`, and delete only that data afterwards. Never assert exact counts against Aura.
- Aura Free pauses after a few days without use. Resume it in the Aura console if the connection fails.

## Team rules

- Plan every larger feature in plan mode first, and commit the agreed plan to `docs/plans/<yyyy-mm-dd>-<feature>.md` before building it.
- Work on a feature branch and merge to `main` through a pull request. Every group member commits.
- Reference the requirement in commits and PRs where it applies (for example "C2: reject quantities below minimum").
- Add or update tests with every feature, and run `pytest` before committing.
- Secrets go in `.env`, which git ignores. Never commit an API key (for example the Claude or image-service key for A2).
- Keep this file short and true. Update it when the layout or commands change.
