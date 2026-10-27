# Plan: A3 Orders and A4 Questions in the admin panel

## Context

The assignment requirements:
- **A3:** "A list of all customer orders that can be filtered by status and event date, and a page per order to manage it: order status (submitted → approved → in preparation → delivered, or rejected/cancelled) and payment status (e.g. not paid, deposit paid, invoiced, paid)."
- **A4:** "Read and answer customers' questions about their orders."

These are the last required features. Already in place:
- `repos().orders.list(status, event_date)` and `get` (`app/models/repositories.py`)
- `OrderStatus` with `label`/`description`, and `PaymentStatus` (`app/models/domain.py`)
- `repos().questions` with `list_for_order`, `answer()` and `list_unanswered()` (C5, #5)
- the admin blueprint with `@admin_required` and the `admin/_nav.html` menu
- the order detail markup in `account/order.html`
- the validation pattern `parse_*` returning `(value, errors)`

Branch `feature/a3-a4-admin-orders`. Commit this plan as `docs/plans/2026-10-27-a3-a4-admin-orders.md`, then open a PR.

## Model layer

- **`order_status.py`** (new): the order state machine, which also goes in the report.
  ```
  ALLOWED = {
    SUBMITTED:      {APPROVED, REJECTED, CANCELLED},
    APPROVED:       {IN_PREPARATION, CANCELLED},
    IN_PREPARATION: {DELIVERED, CANCELLED},
    DELIVERED: {}, REJECTED: {}, CANCELLED: {},      # final
  }
  ```
  - `next_statuses(status)` lists the allowed next statuses.
  - `check_transition(current, new) -> error | None`.
  - `is_open(status)`: true for submitted, approved and in preparation.

  Any payment status can be chosen at any time, because staff sometimes correct mistakes. Changing it to the value it already has does nothing.
- **`repositories.py` / `memory.py` / `neo4j_repos.py`**: add `OrderRepository.update_status(order_id, status=None, payment_status=None) -> Order`. It raises KeyError for an unknown order. Neo4j `SET`s only the fields that are given, plus `statusChangedAt`.
- **`questions.py`**: add `parse_answer(text)`, using the same rules as `parse_question` (required, at most 2000 characters) and `new_answer(text, staff)`.

## Controllers (`app/controllers/admin.py`, all `@admin_required`)

- **`GET /admin/orders/`** (A3 list). Filters come from the query string:
  - `status`: a single status, `open` (the default, for submitted, approved and in preparation) or `all`
  - `event_date`: an exact date, matching `OrderRepository.list`

  The table shows the reference (linking to the order), customer name, event date, guests, total, status, payment and unanswered questions. It's sorted by event date with the soonest first, because that's what the kitchen needs. Customer names come from one `users.get` per distinct customer. An empty result says "No orders match".
- **`GET /admin/orders/<id>`** (A3 order page, 404 for an unknown id). It shows:
  - the event, delivery address, guest groups, lines and total, with the markup shared with the customer page
  - the customer's name, e-mail and phone
  - a status form, a select with only the allowed next statuses (or "final" when there are none)
  - a payment form, a select with all payment statuses
  - all questions, each with an answer form (A4). An existing answer can be edited.
- **`POST /admin/orders/<id>/status`**: calls `check_transition`. An illegal or unknown status flashes an error and changes nothing. Success flashes "Status changed to Approved".
- **`POST /admin/orders/<id>/payment`**: takes a valid `PaymentStatus`, otherwise flashes an error.
- **`POST /admin/questions/<question_id>/answer`** (A4): checks with `parse_answer`. It's 404 if the question isn't on that order (the order id travels in a hidden field). It calls `repos().questions.answer(...)`, then redirects to the order page at `#q-<id>`. An empty answer flashes an error and keeps nothing.
- **`GET /admin/questions/`** (A4 inbox): unanswered questions, oldest first, with the reference, customer and when they were asked, each linking to the order page at that question.
- **`GET /admin/`** still redirects to food items, now through the nav. The admin nav becomes Food items · Orders · Questions (n), where n is the number of unanswered questions, added to admin pages by a small context processor that runs only for admin pages.

## Views

- **`orders/_details.html`** (new shared partial): event facts, guest groups, lines and total, used by both `account/order.html` and `admin/orders/order.html`. The customer page keeps its own questions and ask form.
- **`admin/orders/list.html`**: a filter form (GET) with a status select and a date input, plus the table. On phones it uses the same card pattern as My orders.
- **`admin/orders/order.html`**: status and payment forms side by side, the customer box and the question threads with answer forms.
- **`admin/questions/list.html`**: the inbox.
- CSS: reuse `badge status-*`, `.panel`, `.question` and `.answer`.

## Tests

- **`tests/test_order_status.py`:** every allowed and forbidden transition, the final states and `is_open`.
- **Order repository contract** (memory and Neo4j, extending `tests/test_order_repository.py`): `update_status` changes only what's given, and an unknown id raises KeyError.
- **`tests/test_admin_orders.py`:**
  - The list defaults to open orders. The `status=all`, single-status and `event_date` filters work, and the list is sorted by event date.
  - The order page shows customer contact details and only the allowed next statuses.
  - An allowed change is saved and an illegal one (delivered → approved) is refused.
  - A payment change is saved and an invalid one is refused.
  - An unknown order returns 404, a customer gets 403 and a logged-out visitor is redirected.
- **`tests/test_admin_questions.py`:**
  - the inbox lists unanswered questions, oldest first, and the nav count is right
  - answering removes the question from the inbox, and the customer then sees the answer on their order page
  - editing replaces the answer, and an empty answer is refused
  - a question id paired with the wrong order returns 404, and a customer gets 403
- **End-to-end:** a customer places an order and asks a question. The admin approves the order, marks a deposit as paid and answers. The customer's My orders then shows Approved / Deposit paid and "1 (1 answered)".

## Docs

- `docs/models/`: add the state machine as Mermaid in `order-status.md`, matching `order_status.py`. It replaces the lab state machine for this app, and it notes that the lab model had extra states (Quoted, AwaitingDeposit, …).
- `graph-model.md`: add `statusChangedAt`.
- `CLAUDE.md`: status changes must go through `check_transition`, and the admin nav lists Orders and Questions.
- `README.md`: a short admin tour (food items, pictures, orders, questions).

## Verification

1. `pytest` and `pytest -m neo4j` pass.
2. In the in-memory preview app in the browser:
   - as admin: open Orders (open orders by default), filter by date, open `EM-DEMO01`, approve it, mark a deposit as paid and try an illegal change (the select doesn't even offer it)
   - answer a question, check the Questions count goes down, and edit the answer
   - as customer: My orders shows the new status and the answer
3. Against Aura: approve `EM-DEMO01` through the repository and check `status` and `statusChangedAt` in Neo4j, then set it back to Submitted, so the shared demo data stays as it was.
4. Scan for secrets, then push the branch and open a PR.

## Out of scope

- e-mail notifications, the kitchen day view and the capacity check (optional "going further" ideas)
- a status history or audit log (only the latest `statusChangedAt` is stored)
