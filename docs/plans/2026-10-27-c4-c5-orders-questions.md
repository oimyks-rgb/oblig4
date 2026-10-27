# Plan: C4 My orders and C5 Questions about an order

## Context

The assignment requirements:
- **C4:** "The customer's own orders with their current status (submitted, approved, delivered, …) and payment status."
- **C5:** "Ask a question about a specific order and read Ekte Mat's answer."

C2/C3 (merged in #4) already give us:
- orders through `repos().orders` (`list_for_customer` returns newest first)
- the order detail and confirmation page `account.order` (`/account/orders/<id>`), visible only to the owner or an admin
- `OrderStatus`/`PaymentStatus` with `.label`
- `/account/` is still a placeholder (`app/templates/account/index.html`)

Answering questions belongs to staff (A4, the next plan). This plan builds the question model and repository, including `answer()`, so A4 only needs the admin screens. Until then, the seed creates a demo order with one answered question, so a customer can see an answer in the app.

Branch `feature/c4-c5-orders-questions`. Commit this plan as `docs/plans/2026-10-27-c4-c5-orders-questions.md`, then open a PR.

## Model layer (`app/models/`)

- **`domain.py`**:
  - `Answer(text, answered_at, answered_by_id)`
  - `Question(id, order_id, customer_id, text, asked_at, answer: Answer | None = None)` with an `is_answered` property
  - `OrderStatus.description`: one sentence per status for customers, for example Submitted = "Ekte Mat has received your order and will review it."
- **`questions.py`** (new): `parse_question(text) -> (str, errors)` requires the text, limits it to 1000 characters and trims it. `new_question(order, customer, text)` builds the question.
- **`repositories.py`**: a new `QuestionRepository` with these methods:
  - `add(question)`
  - `list_for_order(order_id)`, oldest first, so it reads like a conversation
  - `list_for_customer(customer_id)`, for the counts on the My orders list
  - `answer(question_id, answer)`, which sets or replaces the answer (used by A4 and the seed)
  - `list_unanswered()`, ready for A4

  Add `Repositories.questions`.
- **`memory.py`**: `MemoryQuestionRepository`.
- **`neo4j_repos.py`**: `Neo4jQuestionRepository`, using the graph model already sketched in `docs/models/graph-model.md`:
  ```
  (:User)-[:ASKED]->(:Question {id, text, askedAt})-[:ABOUT]->(:Order)
  (:User)-[:WROTE]->(:Answer {text, answeredAt})-[:ANSWERS]->(:Question)
  ```
  - `answer()` removes any old `:Answer` before creating the new one.
  - A new constraint makes `Question.id` unique (`neo4j_db.py`).

## Controllers (`app/controllers/account.py`)

- `GET /account/` (C4): the logged-in customer's orders, newest first. The table shows:
  - the reference (linking to the order page) and the event date
  - when the order was placed, using the `local_time` filter
  - status and payment status as badges, and the total
  - "Questions": for example "2 (1 answered)", using one `questions.list_for_customer()` call grouped by order

  When there are no orders, it says so and links to the menu.
- `GET /account/orders/<id>` (existing page, extended for C5):
  - shows the status with its description
  - adds a "Questions about this order" section listing each question with its time and either the answer (with time) or "Waiting for an answer from Ekte Mat"
  - has a form to ask a new question, shown only to the customer who owns the order
- `POST /account/orders/<id>/questions` (`@login_required`, owner only, otherwise 404): calls `parse_question`. On error it re-renders the order page with status 400 and keeps the text. On success it flashes "Your question was sent" and redirects to `#questions`.

## Views

- **`account/index.html`**: the orders table, with a short legend for what the statuses mean.
- **`account/order.html`**: the questions section and the ask form. The textarea has `maxlength=1000` and a hint: "Don't include guests' names or health details beyond what the kitchen needs."
- **`base.html`**: the "My orders" link already exists.

## Seed (demo data for C4/C5 until A4 exists)

- `seed.py` gets `seed_demo_order(repos)`. If it doesn't exist yet, it creates order `seed-order-1` (reference `EM-DEMO01`) for Kari:
  - 15 × Bergen fish soup and 1 × Kransekake
  - an event date 30 days after seeding, with one guest group
  - one question ("Can the fish soup be made without celery?") answered by the seeded admin

  Rerunning doesn't add duplicates. The `--reset` behaviour is unchanged.

## Tests

- `tests/test_question_rules.py`: `parse_question` (empty, too long, trimmed).
- **Question repository contract:** a contract test in `tests/test_question_repository.py` runs against memory, and against Neo4j through `test_neo4j_repos.py`. It checks:
  - add; order and customer listings, including their ordering
  - answering, replacing an answer and `list_unanswered`
  - Neo4j cleanup also removes `:Question` and `:Answer` nodes linked to `test-` orders
- **`tests/test_my_orders.py`:**
  - login is required
  - customers see only their own orders, newest first, with their statuses
  - the empty state works
  - the question counts are right
- **`tests/test_order_questions.py`:**
  - the owner can ask, and the question shows as waiting
  - an answer (added through the repository) is shown
  - an empty or too-long question returns 400 and keeps the text
  - another customer gets 404 for both GET and POST
  - an admin can view the order but sees no ask form
- **`tests/test_seed_images.py`** (or a new `test_seed_demo.py`): `seed_demo_order` is idempotent against the memory backend.

## Docs

- `docs/models/graph-model.md`: move Question and Answer from "planned" to implemented, and add the constraint.
- `CLAUDE.md`: add questions to the layout, and note that answers are created only by staff (A4).
- `README.md`: Kari's demo order shows C4/C5.

## Verification

1. `pytest` and `pytest -m neo4j` pass.
2. In the in-memory preview app in the browser:
   - log in as a customer and place an order
   - My orders lists it as Submitted / Not paid
   - open it, send a question, and see it listed as waiting
   - send an empty question, which shows an error
3. Against Aura: `python seed.py` creates `EM-DEMO01`, and I check the `:Question`/`:Answer` nodes in Neo4j. Logging in as Kari to see the answer in the app is something you can do with the seed password.
4. Scan for secrets, then push the branch and open a PR.

## Out of scope

- A3 (the admin order list and status changes) and A4 (answering questions in the admin panel), which come next
- e-mail notifications about answers
