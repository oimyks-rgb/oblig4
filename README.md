# Ekte Mat Online

A catering web shop and admin panel for Ekte Mat AS, a fictional catering company in Bergen. INFO212 obligatory assignments 4 and 5, built with Flask (MVC) and Neo4j AuraDB.

All data is synthetic.

## Requirements

- Python 3.12+
- Access to a Neo4j AuraDB instance (the group shares one)

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` from the Aura console
- a random `SECRET_KEY`
- the passwords to give the seeded test users

Never commit `.env`.

## Pictures (A2)

Staff can upload a picture for each food item, or have Gemini create or modify one from a written instruction. Either way, the admin previews the new picture before saving it.

- Set `IMAGE_GENERATOR=gemini` and `GEMINI_API_KEY` in `.env` to use Gemini. Image models have no free tier and cost about $0.034 per picture.
- `IMAGE_GENERATOR=fake` draws simple test pictures locally, for free.
- Leave it empty for upload only.

Sample illustrations for the seed items live in `seed_images/` and are committed to git. To make them:

```bash
python generate_images.py --only seed-falafel   # try the style on one item
python generate_images.py                       # the rest
```

`python seed.py` copies them into your local picture folder.

Pictures are stored in `instance/images/` on each computer and are not in git. A picture uploaded on one computer shows as a placeholder on the others. Seed pictures work everywhere, because every machine gives them the same name.

## Seed

```bash
python seed.py
```

This creates constraints, allergen and event-category nodes, 11 food items (with pictures from `seed_images/`), an admin (`admin@ektemat.test`) and two customers (`kari.nordmann@ektemat.test`, `ola.hansen@ektemat.test`). It is safe to rerun: it only adds what is missing and never overwrites changes made in the admin panel. `python seed.py --reset` deletes everything in the database first, so agree in the group before using it.

## Run

```bash
flask --app app run --debug --port 5001
```

Open <http://localhost:5001>. Port 5000 is taken by AirPlay on macOS.

Customers can register at `/account/register`, fill a cart from the menu and place an order at `/order/checkout`. No payment is involved. Under My orders (`/account/`) they see their orders with status and payment status, and they can ask questions about each order.

The seed creates a demo order `EM-DEMO01` for `kari.nordmann@ektemat.test` with an answered question.

The admin panel is at `/admin/`. Log in as `admin@ektemat.test` with the `SEED_ADMIN_PASSWORD` from `.env`. The test customers use `SEED_CUSTOMER_PASSWORD`.

## Test

```bash
pytest              # fast tests with in-memory repositories, no database needed
pytest -m neo4j     # repository tests against the Neo4j database in .env
```

The Neo4j tests only create and delete data with ids starting with `test-` and e-mails ending with `@test.invalid`.

## Project structure

| Path | Layer |
|---|---|
| `app/models/` | Model: domain classes, repository interfaces, Neo4j and in-memory implementations |
| `app/controllers/` | Controller: Flask blueprints `shop`, `account`, `admin` |
| `app/templates/`, `app/static/` | View: Jinja2 templates, CSS, images |
| `docs/` | Requirements, models, graph data model, and feature plans (`docs/plans/`) |

See `CLAUDE.md` for the team rules.
