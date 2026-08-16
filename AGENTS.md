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

- The virtual env `venv` is **not** committed (it is gitignored) and requires Python 3.12. Create it once per machine: `python3.12 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`.
- No tests, no lint config, no CI. Use the script above as the executable source of truth.

---

## Setup

- Copy `.env.example` to `.env` and set `STRATZ_API_KEY`.
- `config.py` validates the key at startup; the app will not launch without it.
- (Optional, Google Drive) set `GOOGLE_DRIVE_CLIENT_SECRETS` (path to an OAuth Desktop-app client secret JSON, e.g. `data/drive_client_secret.json`), `GOOGLE_DRIVE_TOKEN_PATH` (where the OAuth token is saved, default `data/drive_token.json`), and `GOOGLE_DRIVE_FOLDER_ID` to share the `match_ids_*.csv` between the home and Tecsup machines. The first time Drive is used a browser opens to authorize with your Google account; after that the token is refreshed automatically. Without them the app works normally, only the Drive upload/download features are disabled.
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
              │     │     ├── SpecificTopService
              │     │     └── DailyHarvestService
              │     ├── ParseService
              │     ├── ExportService
              │     ├── DriveService
              │     └── AnalysisService
              │
              ├── core/
              │     ├── time.py        (shared helpers)
              │     ├── models.py      (domain dataclasses)
              │     └── replay_store.py (raw replay JSON files)
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

- Main menu: `1. Buscar y almacenar IDs`, `2. Parse`, `3. Exportar data`, `4. Analizar data`, `5. Salir`.
- Search submenu: daily harvest only.
- Parse submenu: parse matches, enqueue parses from a `match_ids` CSV, download parses from a `match_ids` CSV, clean old match IDs.
- Export submenu: export chats/kills, re-export matches parsed today.
- Analysis submenu: export rampages as a combined top (speed + reactions).

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
- `Database.migrate()` adds the `parsed`, `has_replay_data`, `data_verified`, `parse_requested_at`, `parse_request_count`, `parse_job_id`, `parse_status`, `last_parse_attempt_at`, and `unparseable` columns and the `match_details` table to existing databases. `match_details` is only an index: the raw OpenDota JSON lives in per-match files at `data/replays/{match_date}/{match_id}.json` (written by `core/replay_store.py`). `migrate()` also converts legacy databases that stored the JSON inline in an `opendota_data` column by dumping each row to a file and dropping the column.
- `hero_service.ensure_synced()` only syncs heroes once when the table is empty.
- `chat_wheel_service.ensure_synced()` only syncs chat wheels once when the table is empty, using the local `data/chat_wheel.json` catalog.
- `rampage_service.fetch_by_rampages()` is long-running and network-heavy: it queries every hero with a delay (`Config.REQUEST_DELAY = 0.5s`) and retries on errors.
- `Config.RAMPAGE_TAKE` controls how many matches the Stratz API is asked for per hero per run; the local database has no per-hero cap. Only matches that are not already stored (`hero_id`, `match_id`) are inserted, so the DB grows incrementally with each run. **Note:** `RampageService`, `TopHeroesService`, and `SpecificTopService` are legacy discovery services — they still exist and are wired in `ServiceFactory`, but no menu option reaches them anymore. The search submenu only exposes the daily harvest.
- `parse_service.parse_unparsed()` reads up to `Config.PARSE_BATCH_SIZE` matches with `parse_status` in `pending`, `queued`, or `parsing`, calls OpenDota, requests replay parses when needed, polls the returned `jobId`s, saves the full JSON as a replay file under `data/replays/`, and updates status. Failures and 404s are marked `unparseable` so they are not retried. OpenDota requests track 429 responses; after `Config.RATE_LIMIT_MAX_RETRIES` consecutive 429s the client raises `RateLimitError`, `ParseService` pauses for `Config.RATE_LIMIT_PAUSE_SECONDS` (300s by default), and then resumes from the same item. When `Config.PARSE_GET_ONLY` is enabled (default), parsing only issues GETs: matches whose data is already parsed are saved and marked `done`, and matches without replay data are left `pending` to be retried on a later run (no parse jobs are enqueued, no polling).
- `parse_service.clean_old_matches()` deletes matches older than `Config.CLEAN_OLD_MATCHES_DAYS`: it removes the `rampage_matches`/`match_details`/`export_log` rows (filtering by the `match_date` index, no JSON scanning) and the corresponding replay files under `data/replays/`.
- `parse_service.enqueue_from_csv()` (menu `2` → option `2`, run at the institute on a machine with its own OpenDota quota/IP) reads a `exports/match_ids_*.csv`, calls `POST /request/{id}` for every ID with progress `[i/N]` and 429 pause handling, and writes a traceability CSV `exports/parse_jobs_YYYY-MM-DD.csv` (`match_id`, `job_id`). It does not touch the local database.
- `parse_service.download_from_csv()` (menu `2` → option `3`, run at home once parses were enqueued elsewhere) reads a `exports/match_ids_*.csv`, filters the IDs through `MatchRepository.list_downloadable()` (skipping matches already `done` with replay data and `unparseable` ones to save quota), calls `GET /matches/{id}`, saves the full JSON via `save_match_details()`, and marks the match `done`. Matches whose parse is not ready yet stay `pending` so they are retried on a later run.
- `daily_harvest_service.harvest()` collects up to `Config.DAILY_MATCH_TARGET` (2900) new distinct match IDs per run, all at most `Config.DAILY_MATCH_MAX_AGE_DAYS` (7) days old, deduplicated globally against every `match_id` already stored. Phases run in priority order and stop when the target is reached: (1) recent rampages for all heroes (all brackets, `take=20` with the match date inlined in the response), (2) recent matches of pro players (`constants.proSteamAccounts`), (3) top leaderboard players of `Config.SPECIFIC_TOP_HEROES`, (4) most-played heroes from `winWeek`, (5) highest-winrate heroes from `winWeek`. Player matches are fetched in batches of at most `Config.PLAYERS_BATCH_SIZE` (5) accounts per request. `harvest()` returns the sorted list of `match_id`s saved during the run.
- After a daily harvest (menu `1` → option `1`), the CLI automatically calls `ExportService.export_match_ids_csv()` with the IDs saved in that run, writing `exports/match_ids_YYYY-MM-DD.csv` (one `match_id` per row). This file is meant to be shared so the IDs can be parsed by a third party (e.g., another OpenDota API key / IP), while this project keeps its own parse quota for the same IDs.
- `analysis_service.export_top()` (menu `4`) builds a combined rampage ranking from the parsed replay files (no API calls) for a selected date or all dates. It reads only matches with `parse_status = 'done'` and `has_replay_data = 1`, groups them by `played_at` date, and for each match detects the **shortest** 5-kill window (≤18s) among the match's heroes (`racha_seg`). Reactions are chat messages within `Config.ANALYSIS_REACTION_WINDOW_SECONDS` (60s) after the rampage ends; `n_reacciones` counts them and `chats_reaccion` lists them. Scoring is rank-based within the selection: best speed = N points, most reactions = N points, `puntaje_total = puntaje_racha + puntaje_reacciones`. The output is a single CSV per selection at `exports/rampages/rampages_YYYY-MM-DD.csv` (or `rampages_all.csv` for all dates). Matches without a detectable rampage are excluded.
- `drive_service` (`services/drive_service.py`) is the **only** integration with Google Drive: it shares the `match_ids_*.csv` between the home machine and the Tecsup machine. It authenticates as the user via an Installed App OAuth flow (client secrets JSON + locally saved token from `.env`), so uploads use the user's own storage quota; when unconfigured it degrades gracefully (messages in Spanish, app keeps working). `export_match_ids_csv()` uploads the CSV right after generating it. In the parse menu, `_pick_match_ids_csv()` offers to download the most recent `match_ids_*.csv` from Drive when no local file exists. After the home `download_from_csv()` run, if every ID in the CSV is `done` or `unparseable`, the CLI asks whether to delete the CSV locally and on Drive (`cleanup_consumed_csv()`). Excel/chat/kill exports, the rampage ranking, the replay JSONs, and `parse_jobs_*.csv` stay **local only** — nothing else touches Drive.

### Stratz API limits (verified against the live API)

- `heroStats.rampages`: max `take` is 20. The `after`/`before` request params do not reliably filter by timestamp, so date filtering is done client-side using the nested `match.startDateTime`.
- `matches(ids:)`: max 10 IDs per call.
- `players(steamAccountIds:)`: max 5 accounts per call; nested `matches(request:)` accepts `startDateTime`, `heroIds`, and `take` (5 works).
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
