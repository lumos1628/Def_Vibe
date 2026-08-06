# AGENTS.md

This file contains the background, architecture, conventions, and rules for working on the **Stratz Rampage Scraper** project.

---

## Project Goal

A small Python CLI that scrapes Dota 2 matches containing **rampages** from the Stratz GraphQL API, parses replay data through the OpenDota REST API, and exports chat and kill events into daily CSV and Excel reports.

The project is designed to:

- Discover rampage matches by hero, bracket, top players, or recent history.
- Store match metadata locally in SQLite to avoid re-fetching duplicates.
- Parse replays incrementally using OpenDota jobs.
- Produce reproducible, styled datasets for analysis.

---

## Run

```bash
source venv/bin/activate
python main.py
```

- Virtual env `venv` is committed to the repo and uses Python 3.12. Activate it before running.
- No tests, no lint config, no CI. Use the script above as the executable source of truth.

---

## Setup

- Copy `.env.example` to `.env` and set `STRATZ_API_KEY`.
- `config.py` validates the key at startup; the app will not launch without it.
- Install deps if recreating the environment: `pip install -r requirements.txt`.

---

## Architecture

The project follows a strict layered architecture:

```
main.py
  └── cli/ (menus + ServiceFactory)
        └── ServiceFactory
              ├── api/
              │     ├── StratzClient      (GraphQL, cloudscraper)
              │     ├── OpenDotaClient    (REST, rate-limit handling)
              │     └── queries.py        (GraphQL strings)
              │
              ├── services/
              │     ├── HeroService
              │     ├── ChatWheelService
              │     ├── discovery/
              │     │     ├── BaseDiscoveryService
              │     │     ├── RampageService
              │     │     ├── TopHeroesService
              │     │     └── SpecificTopService
              │     ├── ParseService
              │     └── ExportService
              │
              ├── core/
              │     ├── time.py        (shared helpers)
              │     └── models.py      (domain dataclasses)
              │
              ├── repositories/
              │     ├── HeroRepository
              │     ├── MatchRepository
              │     └── ChatWheelRepository
              │
              └── database.py (SQLite)
```

### Entry point

- `main.py` is the only entrypoint.
- It imports `ServiceFactory` from `cli/factory.py`, initializes the SQLite schema (`Database.init`), runs migrations (`Database.migrate`), syncs the hero list, syncs chat wheels, and presents a menu via `cli/menus.py`.

### Menus

- Main menu: `1. Buscar y almacenar IDs`, `2. Parse`, `3. Exportar data`, `4. Salir`.
- Search submenu: top heroes, rampages by bracket, latest rampages, specific top heroes.
- Parse submenu: parse matches, clean old match IDs.
- Export submenu: export chats/kills, re-export matches parsed today.

### Layer responsibilities

- **`api/`** — wraps external HTTP APIs. No business logic.
- **`cli/`** — interactive menus and dependency injection (`ServiceFactory`).
- **`core/`** — shared utilities and domain models.
- **`services/`** — contains all business logic and workflows.
- **`repositories/`** — thin SQLite wrappers; only data access.
- **`database.py`** — schema, connection management, and migrations.
- **`config.py`** — centralized configuration and validation.

---

## Important Behavior

- `main.py` calls `Database.init()` on every startup; the SQLite file `data.db` is the persistent store.
- `Database.migrate()` adds the `parsed`, `has_replay_data`, `data_verified`, `parse_requested_at`, `parse_request_count`, `parse_job_id`, `parse_status`, `last_parse_attempt_at`, and `unparseable` columns and the `match_details` table to existing databases.
- `hero_service.ensure_synced()` only syncs heroes once when the table is empty.
- `chat_wheel_service.ensure_synced()` only syncs chat wheels once when the table is empty, using the local `data/chat_wheel.json` catalog.
- `rampage_service.fetch_by_rampages()` is long-running and network-heavy: it queries every hero with a delay (`Config.REQUEST_DELAY = 0.5s`) and retries on errors.
- `Config.RAMPAGE_TAKE` controls how many matches the Stratz API is asked for per hero per run; the local database has no per-hero cap. Only matches that are not already stored (`hero_id`, `match_id`) are inserted, so the DB grows incrementally with each run.
- `parse_service.parse_unparsed()` reads up to `Config.PARSE_BATCH_SIZE` matches with `parse_status` in `pending`, `queued`, or `parsing`, calls OpenDota, requests replay parses when needed, polls the returned `jobId`s, saves the full JSON in `match_details`, and updates status. Failures and 404s are marked `unparseable` so they are not retried. OpenDota requests track 429 responses; after `Config.RATE_LIMIT_MAX_RETRIES` consecutive 429s the client raises `RateLimitError`, `ParseService` pauses for `Config.RATE_LIMIT_PAUSE_SECONDS` (300s by default), and then resumes from the same item.
- Repository code uses `RETURNING id` and `ON CONFLICT` clauses; queries assume a reasonably modern SQLite (Python 3.12 ships with SQLite 3.45+).

---

## Code Conventions

- **UI strings and comments are in Spanish; code identifiers are in English.**
- Follow the existing layered structure: `api` → `services` → `repositories` → `database`.
- No formatter or linter is configured; keep style consistent with the existing files.
- Use type hints for function signatures and class attributes.
- Use `Path` from `pathlib` for filesystem paths.
- Keep configuration values in `config.py`; use environment variables for secrets.
- Services should be stateless unless they manage client state (e.g., rate-limit counters).
- Repository methods return plain data structures (`list[dict]`, `tuple`, etc.), not domain objects.
- Naming:
  - Classes: `PascalCase`
  - Functions/methods/variables: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`
  - Private helpers: prefix with `_`

---

## Rules for Future Implementations

### Adding a new service

- Create the service under `services/` or `services/discovery/` if it is a discovery service.
- Wire it in `ServiceFactory` (`cli/factory.py`) with its required repositories/clients.
- Add a menu option in `cli/menus.py` if it is user-facing.
- Update this `AGENTS.md` file if the behavior is important for future agents.

### Adding a new GraphQL query

- Define the query string in `api/queries.py`.
- Call it through `StratzClient.execute()`; do not hardcode query strings elsewhere.
- Add retry/exception handling consistent with existing services.

### Adding a new repository

- Create the repository under `repositories/`.
- Keep it a thin wrapper around SQLite.
- Use `ON CONFLICT` for upserts and `RETURNING` when needed.
- Ensure migrations in `database.py` create the corresponding table if it does not exist.

### Adding a new menu

- Add a `show_*_menu()` function and a `run_*_menu()` dispatcher in `cli/menus.py`.
- Follow the existing pattern of validating input and returning `None` for invalid choices.

### Adding a new export format

- Extend `ExportService` or create a new export service.
- Respect the existing CSV/Excel fieldname lists when adding columns.
- Update `docs/csv_format.md` if the output format changes.

### Adding new configuration

- Add the constant to `config.py` with a sensible default.
- If it must come from the environment, add it to `.env.example`.
- Document the new option in this file if it affects behavior significantly.

---

## Rules for Tests

- **There are currently no tests in this project.**
- If tests are added in the future:
  - Use `pytest`.
  - Place tests in a `tests/` directory at the project root.
  - Mock external API calls (`StratzClient`, `OpenDotaClient`); never hit real APIs in tests.
  - Use an in-memory SQLite database (`:memory:`) for repository tests.
  - Do not modify the real `data.db` during tests.
  - Keep tests focused on one behavior per test function.
  - Add a `pytest.ini` or `pyproject.toml` section only if necessary.

---

## Rules for Commits

- Write concise, descriptive commit messages in English or Spanish, matching the repo style.
- One commit per logical change.
- Do not commit `data.db`, `.env`, `exports/`, `__pycache__/`, or any generated artifact.
- Inspect `git status` and `git diff` before committing.
- Do not commit secrets or API keys.
- Do not force-push or rewrite public history.
- If the commit message style in the repo is unclear, use the format: `[area] short description`, e.g., `docs: update AGENTS.md`.

---

## Rules for Modifying Files

- Make minimal, focused changes.
- Do not change existing logic unless necessary for the feature or fix.
- Do not rename files without updating every import that references them.
- Do not delete files without explicit user confirmation.
- Keep `main.py` as the only entrypoint.
- Any change to `config.py` that introduces a new environment variable must also update `.env.example`.
- If you modify the database schema, update both `Database.init()` and `Database.migrate()`.
- If you modify the export format, update `docs/csv_format.md`.
- If you modify the data model, update `docs/data_model.md`.

---

## What Must Never Break

These invariants are critical to the project's correct operation:

- `main.py` must remain the only entrypoint.
- `Config.validate()` must continue to require `STRATZ_API_KEY` at startup.
- `Database.init()` followed by `Database.migrate()` must run on every startup.
- Hero and chat wheel synchronization must remain lazy (only sync when the table is empty).
- The layered architecture order must not be inverted: `api` → `services` → `repositories` → `database`.
- The `UNIQUE(hero_id, match_id)` constraint on `rampage_matches` must be preserved.
- The `.gitignore` must continue to exclude `.env`, `data.db`, `exports/`, and `__pycache__/`.
- No secrets may be committed to the repository.

---

## Documentation Rules

- Add docstrings to new public classes and functions.
- Write comments in Spanish to match the existing codebase.
- If you add a new menu option, document it in this `AGENTS.md` file.
- If you add or change an export format, update `docs/csv_format.md`.
- If you add or change a database table or column, update `docs/data_model.md`.
- If you add or change a module's responsibilities, update `docs/modules.md`.
- Keep `README.md` as the high-level entry point; put detailed documentation under `docs/`.

---

## Language / Conventions Summary

- UI strings and comments: **Spanish**
- Code identifiers and docstrings: **English**
- Commit messages: **English or Spanish**, consistent with the repo
- Documentation: **English** for `AGENTS.md`, `README.md`, and `docs/`
