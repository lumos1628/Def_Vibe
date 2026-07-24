# AGENTS.md

Small Python CLI that scrapes Dota 2 rampage matches from the Stratz GraphQL API and stores them in a local SQLite database.

## Run

```bash
source venv/bin/activate
python main.py
```

- Virtual env `venv` is committed to the repo and uses Python 3.12. Activate it before running.
- No tests, no lint config, no CI, no README. Use the scripts above as the executable source of truth.

## Setup

- Copy `.env.example` to `.env` and set `STRATZ_API_KEY`.
- `config.py` validates the key at startup; the app will not launch without it.
- Install deps if recreating the environment: `pip install -r requirements.txt`.

## Architecture

- `main.py` is the only entrypoint. It builds `ServiceFactory`, initializes the SQLite schema (`Database.init`), runs migrations (`Database.migrate`), syncs the hero list, and presents a menu.
- Main menu: `1. Buscar y almacenar IDs`, `2. Parsear partidas con OpenDota`, `3. Salir`. The `1. Buscar y almacenar IDs` sub-menu groups multiple search methods; rampages is currently option `2`.
- `api/client.py` wraps the Stratz GraphQL endpoint using `cloudscraper` (Cloudflare bypass) and `requests` with retries.
- `api/opendota_client.py` wraps the OpenDota REST API with a 1 req/s delay and retries.
- `api/queries.py` holds the GraphQL query strings.
- `services/hero_service.py` fetches and caches the hero list.
- `services/rampage_service.py` iterates all heroes and stores rampage matches; each match requires a second GraphQL call to fetch the date.
- `services/parse_service.py` iterates unparsed matches, fetches the full match JSON from OpenDota, and stores it in `match_details`.
- `repositories/hero_repository.py` and `match_repository.py` are thin SQLite wrappers.

## Important behavior

- `main.py` calls `Database.init()` on every startup; the SQLite file `data.db` is the persistent store.
- `Database.migrate()` adds the `parsed` column and `match_details` table to existing databases.
- `hero_service.ensure_synced()` only syncs heroes once when the table is empty.
- `rampage_service.fetch_by_rampages()` is long-running and network-heavy: it queries every hero with a delay (`Config.REQUEST_DELAY = 0.5s`) and retries on errors.
- `Config.RAMPAGE_TAKE` controls how many matches the Stratz API is asked for per hero per run; the local database has no per-hero cap. Only matches that are not already stored (`hero_id`, `match_id`) are inserted, so the DB grows incrementally with each run.
- `parse_service.parse_unparsed()` reads matches with `parsed = 0`, calls OpenDota once per match, saves the full JSON in `match_details`, and marks the match as parsed. Failures and 404s are also marked parsed so they are not retried.
- Repository code uses `RETURNING id` and `ON CONFLICT` clauses; queries assume a reasonably modern SQLite (Python 3.12 ships with SQLite 3.45+).

## Language / conventions

- UI strings and comments are in Spanish; code is English.
- Follow the existing layered structure: `api` → `services` → `repositories` → `database`.
- No formatter or linter is configured; keep style consistent with the existing files.
