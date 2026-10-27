# Graph data model (Neo4j)

Current version, as implemented in `app/models/neo4j_repos.py`. Extend it as features are added: orders, order lines, guest-group diets and questions.

```mermaid
graph LR
  F["FoodItem<br/>id, name, description,<br/>priceNok, minOrderQty,<br/>dietaryLabels[], published,<br/>noAllergens, imageFilename"]
  A["Allergen<br/>code, name"]
  C["EventCategory<br/>code, name"]
  U["User<br/>id, email, name,<br/>passwordHash, role"]
  F -- CONTAINS --> A
  F -- SUITS --> C
```

## Constraints

Created by `ensure_schema()` in `app/models/neo4j_db.py`:
- `FoodItem.id` is unique.
- `User.id` and `User.email` are unique. E-mail is stored in lowercase.
- `Allergen.code` and `EventCategory.code` are unique.

## Mapping from the domain model

| Domain class (`app/models/domain.py`) | Graph |
|---|---|
| `FoodItem` | `:FoodItem` node |
| `FoodItem.allergens` | `CONTAINS` relationships to `:Allergen` nodes (the 14 EU allergens) |
| `FoodItem.event_categories` | `SUITS` relationships to `:EventCategory` nodes |
| `FoodItem.dietary_labels` | List property on the node |
| `FoodItem.image_filename` | `imageFilename`: content-hash name (`<32 hex>.jpg`) of a file in the image store, not stored in the graph itself |
| `FoodItem.no_allergens` | `noAllergens` property: staff confirmed the item has none of the 14 allergens (US-33) |
| `User` (customers and admins) | `:User` node, where `role` is `customer` or `admin` |

## Why allergens and event categories are nodes

Allergens and event categories are nodes rather than list properties, because the planned features query along them. The menu by event (C1) and the kitchen view of the day's orders with allergies highlighted (Mateo) can then be written as traversals, for example `(:Order)-[:INCLUDES]->(:FoodItem)-[:CONTAINS]->(:Allergen {code: 'nuts'})`.

Dietary labels are only displayed, so they stay a simple property.

## Planned extension

For C2–C5 and A3–A4:

```
(:User)-[:PLACED]->(:Order {status, paymentStatus, eventDate, guestCount, deliveryAddress})
(:Order)-[:INCLUDES {quantity, unitPriceNok}]->(:FoodItem)
(:Order)-[:HAS_DIET]->(:GuestGroupDiet {guestCount, diet, note})
(:User)-[:ASKED]->(:Question {text, askedAt})-[:ABOUT]->(:Order)
(:Question)<-[:ANSWERS]-(:Answer {text, answeredAt})
```
