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
- Main menu: `1. Buscar y almacenar IDs`, `2. Parse`, `3. Exportar data`, `4. Salir`. The `1. Buscar y almacenar IDs`, `2. Parse`, and `3. Exportar data` sub-menus group multiple methods; rampages is currently option `2` under search, `Parsear` is option `1` under Parse, `Limpiar IDs antiguas` is option `2` under Parse, and `Exportar kills y chats` is option `1` under export.
- `api/client.py` wraps the Stratz GraphQL endpoint using `cloudscraper` (Cloudflare bypass) and `requests` with retries.
- `api/opendota_client.py` wraps the OpenDota REST API with a 1 req/s delay and retries.
- `api/queries.py` holds the GraphQL query strings.
- `services/hero_service.py` fetches and caches the hero list.
- `services/chat_wheel_service.py` loads the local Dota 2 chat wheel catalog (`data/chat_wheel.json`) into the `chat_wheels` table on first run.
- `services/rampage_service.py` iterates all heroes and stores rampage matches; each match requires a second GraphQL call to fetch the date.
- `services/parse_service.py` processes a configurable batch of matches (`Config.PARSE_BATCH_SIZE`) in phases: (1) verify each match with `GET /matches/{match_id}` and save the JSON; (2) enqueue matches without replay data via `POST /api/request/{match_id}` and store the returned `jobId`; (3) poll `GET /request/{jobId}` for up to `Config.PARSE_MAX_POLLS` rounds, waiting `Config.PARSE_POLL_INTERVAL` seconds between rounds; (4) fetch the parsed data with `GET /matches/{match_id}`. Matches older than `Config.MAX_REPLAY_AGE_DAYS` are marked `unparseable` and not retried. After a successful verification call, the match is flagged `data_verified = 1` so a restart skips the `GET` call and goes directly to enqueueing/polling.
- `services/export_service.py` reads stored match JSON, translates chat wheel IDs to their real text using the `chat_wheels` table, detects the rampage time from the kill log, and exports two separate flat files: chats and kills. For each day it creates a folder `exports/YYYY-MM-DD/` containing `chats.csv`, `kills.csv`, and a styled dark-mode Excel workbook `rampage_export_YYYY-MM-DD.xlsx` with two sheets: "Chats" and "Kills". The `chats.csv` sheet includes the chat message, its time, and the sender hero (mapped from `player_slot`). The `kills.csv` sheet includes who killed whom, the rampage time, and a flag `is_rampage_kill` for the kills that form the detected rampage window. Matches without chats or kills are omitted from the files; every processed match is still marked exported so it is not retried on subsequent runs.
- `repositories/hero_repository.py`, `match_repository.py`, and `chat_wheel_repository.py` are thin SQLite wrappers.

## Important behavior

- `main.py` calls `Database.init()` on every startup; the SQLite file `data.db` is the persistent store.
- `Database.migrate()` adds the `parsed`, `has_replay_data`, `data_verified`, `parse_requested_at`, `parse_request_count`, `parse_job_id`, `parse_status`, `last_parse_attempt_at`, and `unparseable` columns and the `match_details` table to existing databases.
- `hero_service.ensure_synced()` only syncs heroes once when the table is empty.
- `chat_wheel_service.ensure_synced()` only syncs chat wheels once when the table is empty, using the local `data/chat_wheel.json` catalog.
- `rampage_service.fetch_by_rampages()` is long-running and network-heavy: it queries every hero with a delay (`Config.REQUEST_DELAY = 0.5s`) and retries on errors.
- `Config.RAMPAGE_TAKE` controls how many matches the Stratz API is asked for per hero per run; the local database has no per-hero cap. Only matches that are not already stored (`hero_id`, `match_id`) are inserted, so the DB grows incrementally with each run.
- `parse_service.parse_unparsed()` reads up to `Config.PARSE_BATCH_SIZE` matches with `parse_status` in `pending`, `queued`, or `parsing`, calls OpenDota, requests replay parses when needed, polls the returned `jobId`s, saves the full JSON in `match_details`, and updates status. Failures and 404s are marked `unparseable` so they are not retried. OpenDota requests track 429 responses; after `Config.RATE_LIMIT_MAX_RETRIES` consecutive 429s the client raises `RateLimitError`, `ParseService` pauses for `Config.RATE_LIMIT_PAUSE_SECONDS` (300s by default), and then resumes from the same item.
- Repository code uses `RETURNING id` and `ON CONFLICT` clauses; queries assume a reasonably modern SQLite (Python 3.12 ships with SQLite 3.45+).

## Language / conventions

- UI strings and comments are in Spanish; code is English.
- Follow the existing layered structure: `api` → `services` → `repositories` → `database`.
- No formatter or linter is configured; keep style consistent with the existing files.
