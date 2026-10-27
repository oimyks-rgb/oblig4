# Plan: C1 Menu by event (finish and document)

## Context

The assignment says C1 is "Food items as cards, grouped by kind of event: birthday, confirmation, wedding, conference, Christmas party (julebord) and so on. Each card shows picture, price, minimum order and allergens."

C1 was built in pieces and never had its own plan:
- the cards and grouping came with the skeleton (#1)
- the pictures came with A2 (#3)
- the add-to-cart field came with C2 (#4)

A review found four gaps:
1. Items marked "contains none of the 14 allergens" (`FoodItem.no_allergens`, US-33) show nothing on the card, so customers can't tell that from "not declared".
2. Items appear under every event they suit, so a long menu repeats them, and there's no quick way to find one kind of event.
3. No test checks that the picture and minimum order are on the card.
4. There's no plan in `docs/plans/`.

The code involved:
- `shop.index` in `app/controllers/shop.py` builds the `sections` list, one per `EventCategory` that has published items
- `app/templates/shop/index.html` renders the cards
- `app/templates/admin/food_items/_picture.html` renders the picture or the placeholder
- `FoodItemRepository.list(published_only, category)` already filters by category in both memory and Neo4j

Branch `feature/c1-menu-by-event`. Commit this plan as `docs/plans/2026-10-27-c1-menu-by-event.md`, then open a PR and move the `oblig4` tag after the merge.

## Changes

- **Event filter** (`shop.index`):
  - The menu accepts `?event=<category code>`, for example `/?event=wedding`, and then shows only that section, using `repos().food_items.list(published_only=True, category=…)`.
  - Without it, the menu shows all sections as now.
  - An unknown code flashes "Unknown event type; showing the whole menu" and shows everything.
  - The controller passes `available` (the categories that have published items, in enum order) and `selected`.
- **Event navigation** (`shop/index.html`): above the sections, a row of links: "All events" followed by one per available category. The current one is marked with `aria-current="page"`. The links use `?event=`, so they work without JavaScript and can be shared. Each section gets `id="event-<code>"`.
- **Allergen line on the card:**
  - "Contains: …" when the item has allergens
  - "No allergens" when `no_allergens` is set
  - nothing otherwise, which can only happen for unpublished items and so never shows on the menu
- **Card markup:** the minimum order is shown as "Minimum order: N portions". Everything else stays the same: picture, name, description, price, dietary tags and add to cart.
- **CSS:** event links in the style of the badges (`.event-nav`), wrapping on phones.

## Tests (`tests/test_menu.py`; the menu test in `test_app.py` moves here)

- The cards show the picture URL (`/images/<name>`) for an item with a picture, and the placeholder for one without.
- The cards show the price, "Minimum order: 10 portions", "Contains: Fish, Milk" and the dietary tags.
- An item with `no_allergens` shows "No allergens".
- The menu is grouped by event: one `<h2>` per category with items, in enum order. An item suiting two events appears in both sections, and unpublished items never appear.
- The event navigation lists only categories that have items. `?event=wedding` shows only the wedding section and marks the link as current, and an unknown code shows everything with the message.

## Docs

- `README.md`: one line on the menu (grouped by event, filter with `?event=`).
- `CLAUDE.md`: the menu is `shop.index`, with event codes from `EventCategory`.

## Verification

1. `pytest` and `pytest -m neo4j` pass.
2. In the browser, against Aura at `localhost:5001`:
   - the menu shows the event links
   - clicking Wedding shows only wedding items with pictures, price, minimum order and allergens
   - "All events" brings back every section
   - phone width looks fine
3. Push the branch and open a PR. After the merge, move the `oblig4` tag to the new `main` and force-push it (you approve this when you ask for the merge).
