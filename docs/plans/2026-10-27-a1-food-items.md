# Plan: A1 Food items in the admin panel (+ admin login)

## Context

Assignment requirement A1: staff add, edit and remove the food Ekte Mat caters. Each item has a name, description, price in NOK, minimum order quantity, event categories, allergens, dietary labels and a published flag. The backlog backs this up:
- US-32: the chef edits dishes and prices without a developer.
- US-33: an item can't be published until its allergens are declared, with "none" chosen explicitly if it has none.

The skeleton (merged in PR #1) already has `FoodItem`, `FoodItemRepository` (list/get/add/update/delete) in both Neo4j and memory versions, and a read-only `/admin/` table. Because A1 adds write actions, `/admin` gets a simple login for the seeded admin (agreed). Customer login and registration (C3) will reuse the same code later. Images (A2) are out of scope: `image_filename` is kept unchanged on edit.

Branch `feature/a1-food-items`. Commit this plan as `docs/plans/2026-10-27-a1-food-items.md`, then open a PR to `main`.

## Model layer (`app/models/`)

- `domain.py`: add `FoodItem.no_allergens: bool = False`. It is set when staff confirm the item contains none of the 14 allergens.
- `food_items.py` (new): `parse_food_item(form: Mapping, item_id: str | None, image_filename=None) -> tuple[FoodItem, dict[str, str]]` turns raw form values into a `FoodItem` plus a field→message error dict. It also provides `new_food_item_id()` (uuid4 hex). Rules:
  - The name is required (at most 100 characters). The description is optional (at most 1000 characters).
  - The price is a whole number of NOK, at least 1. The minimum order quantity is a whole number, at least 1.
  - Category, allergen and dietary codes must be valid enum values.
  - Publishing requires at least one event category, otherwise the item would never show on the C1 menu.
  - Publishing requires declared allergens: at least one allergen, or `no_allergens` (US-33). Selecting both is an error.
  - The `gluten_free` label together with the gluten allergen is an error.
- `accounts.py` (new): `authenticate(users: UserRepository, email, password) -> User | None` using `werkzeug.security.check_password_hash`.
- `neo4j_repos.py`: map `noAllergens` in `_food_item_params` and `_to_food_item` (default False). The memory version needs no change.

## Controllers

- `app/controllers/auth.py` (new, about 40 lines):
  - A `before_app_request` hook loads `g.user` from `session["user_id"]` via `repos().users.get`.
  - A context processor exposes `current_user` to templates.
  - Decorators: `login_required` redirects to `account.login?next=…`. `admin_required` does the same when logged out and returns 403 for a logged-in customer.
- `account.py`:
  - `GET/POST /account/login`: `session.clear()` then set `user_id`. Only a relative `next` is followed. A wrong e-mail or password shows a generic error.
  - `POST /account/logout`.
- `admin.py`: every route uses `@admin_required`.
  - `GET /admin/` redirects to the food item list.
  - `GET /admin/food-items/`: a table of all items (name, price, minimum order, categories, allergens, published), with Edit, Publish/Unpublish and Delete per row.
  - `GET/POST /admin/food-items/new` and `GET/POST /admin/food-items/<id>/edit`: on validation errors, return 400 and re-render the form with the input kept and a message next to each field. On success, flash a message and redirect to the list. Edit returns 404 for an unknown id.
  - `POST /admin/food-items/<id>/publish` toggles the published flag. It runs the same validation, so an item with undeclared allergens can't be published.
  - `POST /admin/food-items/<id>/delete` deletes after a JS `confirm()`. This is a hard delete for now. Once orders exist (C3), deleting an item that has been ordered should be blocked in favour of unpublishing. That's noted in the code and the plan.
- CSRF: add `Flask-WTF` and enable only `CSRFProtect(app)` in `create_app`. Every form gets `{{ csrf_token() }}`. `TestConfig` sets `WTF_CSRF_ENABLED = False`, and one test turns it back on.
- Session cookie: `SESSION_COOKIE_SAMESITE="Lax"`.

## Views (`app/templates/`)

- `base.html`: flash messages. The nav shows Log in or Log out (as a POST form), and the Admin link appears only for admins.
- `account/login.html`
- `admin/food_items/list.html` and `admin/food_items/form.html`. The form has checkbox groups for categories, allergens and dietary labels, a "Contains none of the 14 allergens" checkbox, and a Published checkbox. One form serves both new and edit.
- `main.css`: styles for forms, errors, flash messages and buttons.

## Tests

- `tests/conftest.py`: an `admin_client` and a `customer_client` fixture that add a user with a hashed password to the memory repository and log in through `/account/login`.
- `tests/test_food_item_rules.py`: unit tests for `parse_food_item`, covering each rule above.
- `tests/test_admin_food_items.py`:
  - Create a valid item, which appears in the list and on the shop menu once published.
  - Invalid input returns 400 and keeps what was typed.
  - Edit works, and an unknown id returns 404.
  - Publish is blocked without declared allergens.
  - Delete works.
  - A logged-out visitor is redirected to login, and a customer gets 403.
  - With CSRF enabled, a POST without a token is rejected.
- `tests/test_auth.py`: a good login, a wrong password, `next` handling (an external URL is ignored) and logout.
- Update `tests/test_app.py`: `/admin/` now redirects when logged out.
- The `no_allergens` round-trip is added to the shared repository contract test, so it also runs against Neo4j.

## Docs

- `docs/models/graph-model.md`: add `noAllergens`.
- `CLAUDE.md`: note `admin_required`/`login_required` in `controllers/auth.py`, the rule that validation lives in the model layer (`models/food_items.py` pattern), and CSRF on every form.
- `README.md`: log in to the admin panel as `admin@ektemat.test` with `SEED_ADMIN_PASSWORD`.

## Verification

1. `pytest` (in-memory) and `pytest -m neo4j` (Aura) both pass.
2. Run `python seed.py` again. Existing items still load, because a missing `noAllergens` defaults to False.
3. Run the app on port 5001 and, in the browser pane:
   - log in as admin
   - create an item with no allergens declared and try to publish it, which should be blocked with a message
   - tick "none", publish it and check that it shows on the menu under its category
   - edit its price, unpublish and delete it
   - log in as a customer and check that `/admin/` returns 403
4. Before pushing: no secrets in the diff, and `.env` is not tracked. Then push the branch and open a PR.
