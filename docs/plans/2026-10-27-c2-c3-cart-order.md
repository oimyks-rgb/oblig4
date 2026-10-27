# Plan: C2 Shopping cart and C3 Order (with customer registration)

## Context

The assignment requirements:
- **C2:** add, change and remove items, with an estimated total. Quantities below an item's minimum order are not accepted.
- **C3:** log in or register, then submit the order: event date, number of guests, delivery address, and allergy and dietary notes per guest group. No payment.

The backlog adds:
- **US-02:** the order is stored with a reference number, and the form shows which field to fix and keeps what was typed.
- **US-36:** allergies are stored per guest group as a count plus a type, with **no guest names** (GDPR art. 9).

Already in place (A1/A2 merged in #2/#3):
- `FoodItem` with `min_order_qty` and `published`, through `repos().food_items`
- session login with `login_required`/`admin_required` (`app/controllers/auth.py`)
- `authenticate()` (`app/models/accounts.py`) and CSRF on all forms
- `OrderStatus`/`PaymentStatus` enums (`app/models/domain.py`)
- the validation pattern `parse_* -> (object, errors)` (`app/models/food_items.py`)
- the menu card template (`app/templates/shop/index.html`)

This also completes the A1 TODO: once orders exist, staff can't delete a food item that has been ordered.

Branch `feature/c2-c3-cart-order`. Commit this plan as `docs/plans/2026-10-27-c2-c3-cart-order.md`, then open a PR.

## Model layer (`app/models/`)

- **`domain.py`**: add three classes.
  - `OrderLine(food_item_id, name, unit_price_nok, quantity)` with `line_total`. The name and price are copied when the order is placed, so later menu changes don't alter old orders.
  - `GuestGroup(guest_count, note)`. There's no name field (US-36).
  - `Order` with these fields:
    - `id`, `reference` (for example `EM-7K3QX9`), `customer_id`, `created_at`
    - `event_date`, `event_category`, `guest_count`, `delivery_address`, `phone`
    - `lines`, `guest_groups`, `comment`
    - `status=SUBMITTED`, `payment_status=NOT_PAID`
    - `total_nok` (a property)
- **`cart.py`** (new): the cart is a plain `{item_id: quantity}` dict, kept in the Flask session by the controller.
  - `validate_quantity(item, qty) -> error | None`: a whole number of at least `min_order_qty` and at most 10 000.
  - `cart_lines(cart, food_items) -> (lines, notices)`: looks up current items. Items that were unpublished or deleted are dropped, with a notice.
  - `cart_total(lines)`
- **`orders.py`** (new)
  - `parse_checkout(form, lines, customer, today) -> (Order, errors)` checks these rules:
    - **Event date:** a valid date, at least **3 days ahead** (an assumption, as a constant `MIN_LEAD_DAYS` that's easy to change) and at most a year ahead.
    - **Guests:** between 1 and 2000.
    - **Address:** street is required, the postcode is 4 digits, and the city is required.
    - **Phone:** optional, 8 to 15 digits, with spaces or `+` allowed.
    - **Event category:** optional, chosen from `EventCategory`.
    - **Guest groups:** submitted as repeated `group_count[]`/`group_note[]` fields. Empty rows are ignored, each group needs a count of at least 1 and a note of at most 200 characters, and the counts can't add up to more than the number of guests.
    - **Cart:** it must not be empty, and every line must still meet its minimum.
  - `new_reference()` gives `EM-` plus 6 characters from an alphabet without 0/O/1/I. The repository retries if a reference is already taken.
- **`accounts.py`**: `register_customer(users, name, email, password, confirm) -> (User | None, errors)`.
  - The name is required.
  - The e-mail must be valid and not already registered. The message stays neutral but still says the address is in use, which is fine for this course.
  - The password must be at least 10 characters and match the confirmation.
  - The password is hashed with werkzeug.
- **`repositories.py`**:
  - a new `OrderRepository` with `add(order)`, `get(order_id)`, `list_for_customer(customer_id)` (newest first) and `list(status=None, event_date=None)`, the last one ready for A3
  - `FoodItemRepository.is_ordered(item_id) -> bool`
  - `Repositories.orders`
- **`memory.py`**: `MemoryOrderRepository`, plus `is_ordered` in the memory food item repository, which needs access to orders. Both are built together in `memory_repositories()`.
- **`neo4j_repos.py`**: `Neo4jOrderRepository`, using this graph model:
  ```
  (:User)-[:PLACED]->(:Order {id, reference, createdAt, eventDate (date), eventCategory, guestCount,
                               deliveryAddress, phone, comment, status, paymentStatus})
  (:Order)-[:INCLUDES {quantity, unitPriceNok, name}]->(:FoodItem)
  (:Order)-[:HAS_GUEST_GROUP]->(:GuestGroup {guestCount, note, position})
  ```
  - `add` writes the order in one transaction.
  - Two new constraints: unique `Order.id` and unique `Order.reference`.
  - `is_ordered` is `EXISTS { (:Order)-[:INCLUDES]->(:FoodItem {id: $id}) }`.
  - Neo4j `date` values are converted to Python `date` and back.

## Controllers

- **`shop.py`** (C2):
  - `POST /cart/add`: takes `item_id` and `quantity`, which defaults to the item's minimum. If the item is in the cart already, the quantities are added together. A quantity below the minimum is refused with a flash message such as "Minimum order for Kransekake is 1".
  - `GET /cart`: shows the lines with name, unit price, quantity input, line total and minimum, the estimated total, and "Go to checkout".
  - `POST /cart/update`: updates all quantities at once. Quantity 0 removes a line. Lines below the minimum are kept at their old value, with an error next to the line.
  - `POST /cart/remove`: removes one item.
  - The cart lives in `session["cart"]`, so it works without logging in and survives the login.
  - A context processor shows the number of portions in the cart in the nav ("Cart (3)").
- **`account.py`** (C3):
  - `GET/POST /account/register`: on success, the customer is logged in and redirected to `next`, or to the cart. The login page links to registration and keeps `next`.
  - `GET /account/orders/<order_id>`: a confirmation and detail page. Only the customer who owns the order (or an admin) can open it, and anyone else gets 404. The C4 list comes later and reuses this page.
- **`orders.py` controller** (new blueprint `order`, under `/order`, `@login_required`):
  - `GET/POST /order/checkout`: an empty cart redirects to the menu.
  - On errors, it returns 400 and re-renders the form with the input and the guest-group rows kept.
  - On success, it saves the order, clears the cart, flashes "Order EM-… submitted" and redirects to the confirmation page.
- **`admin.py`**: `delete_food_item` refuses to delete an item that has been ordered. It shows "has been ordered; unpublish it instead".

## Views

- **`shop/index.html`**: each card gets a small form with a quantity field (`min=item.min_order_qty`, defaulting to the minimum) and an "Add to cart" button.
- **`shop/cart.html`**: a table with update and remove buttons, the estimated total, a note that prices are estimates until Ekte Mat approves the order, and "Go to checkout".
- **`order/checkout.html`**:
  - an order summary that can't be edited, with a link back to the cart
  - the event date (`type=date`, `min` = today + 3), event type, number of guests, address fields and phone
  - a "Guest groups with allergies or special diets" section with 3 empty rows (count + note, for example "2 guests: nut allergy"), plus an "Add group" button using a small piece of JS that clones a row. It still works without JS, with the 3 rows.
  - a comment field
  - the text "No payment now. Ekte Mat will confirm your order."
- **`account/register.html`** and **`account/order.html`** (the confirmation page): the reference, status, payment status, lines, total, event details and guest groups.
- **`base.html`**: the cart link with its count. The nav shows "Register" when logged out.

## Tests

- `tests/test_cart.py`: `validate_quantity`, `cart_lines` (unpublished and deleted items dropped with a notice) and the total.
- `tests/test_order_rules.py`: each `parse_checkout` rule, including the lead time, the guest-group sum and that empty rows are ignored. `today` is passed in, so the tests don't depend on the date.
- `tests/test_shop_cart.py`:
  - add (default minimum, adding to an existing line, below minimum refused, unpublished item refused)
  - update, including setting 0 to remove
  - remove, and the cart count in the nav
- `tests/test_checkout.py`:
  - checkout requires login, and the cart survives login and registration
  - a successful order is stored with its lines, prices, guest groups and reference; the cart is cleared; and the confirmation page shows the reference
  - errors return 400 and keep the input
  - another customer gets 404 on the order page
  - ordered items can't be deleted in the admin panel
- `tests/test_register.py`: success leads to being logged in, plus a duplicate e-mail, a short password and a mismatched confirmation.
- **Shared order repository contract:** one contract test (add, get, `list_for_customer`, list with filters, unique reference, `is_ordered`) runs against both the memory and Neo4j repositories. The Neo4j version uses `test-` ids and `@test.invalid` customers, and cleans up `:Order` and `:GuestGroup` nodes linked to them.

## Docs

- `docs/models/graph-model.md`: move the Order part from "planned" to implemented, and add the constraints.
- `CLAUDE.md`: the cart in the session; orders snapshot names and prices; no guest names (US-36); and that ordered items can't be deleted.
- `README.md`: customers can register at `/account/register`, or use the seeded test customers.

## Verification

1. `pytest` and `pytest -m neo4j` pass.
2. In the in-memory preview app in the browser, with CSRF on:
   - add two items (one below its minimum, which is refused), change a quantity and remove one
   - go to checkout, register a new customer, fill in the form with one invalid field (the error shows and the input is kept), fix it and submit
   - check the confirmation page with its reference, and that the cart is now empty
3. Against Aura (`flask run`), you place one order as a seeded customer, and I check in Neo4j that the `:Order`, `INCLUDES` and `:GuestGroup` nodes and relationships exist.
4. Check that no secrets are in the diff, then push the branch and open a PR.

## Out of scope (next plans)

- C4 (My orders list) and C5 (questions)
- A3 (the admin order list and status changes) and A4
- confirmation e-mails (US-03) and the capacity check (US-10)
