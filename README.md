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

## Seed

```bash
python seed.py
```

This creates constraints, allergen and event-category nodes, 11 food items, an admin (`admin@ektemat.test`) and two customers (`kari.nordmann@ektemat.test`, `ola.hansen@ektemat.test`). It is safe to rerun. `python seed.py --reset` deletes everything in the database first, so agree in the group before using it.

## Run

```bash
flask --app app run --debug --port 5001
```

Open <http://localhost:5001>. The admin panel is at `/admin/`. Port 5000 is taken by AirPlay on macOS.

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
