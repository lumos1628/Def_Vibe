# Architecture

## Overview

The project follows a layered architecture:

```
┌─────────────────────────────────────┐
│           main.py                   │
│      Entry point, orchestration     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│              cli/                   │
│  factory.py  →  dependency injection │
│  menus.py    →  interactive CLI     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Services (business logic)         │
│  discovery/ (daily harvest, legacy) │
│  hero, chat_wheel, parse, export,   │
│  analysis, drive                    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Repositories (data access)        │
│ hero, match, chat_wheel             │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Database (SQLite persistence)     │
│         database.py                 │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   External APIs                     │
│ Stratz GraphQL, OpenDota REST,      │
│ Google Drive API                    │
└─────────────────────────────────────┘

Shared utilities live in core/:
- core/time.py       → timestamp parsing
- core/models.py     → domain dataclasses
- core/replay_store.py → per-match replay JSON files
```

## Layers

### `api/`

- **`StratzClient`** (`api/client.py`) — wraps the Stratz GraphQL endpoint using `cloudscraper` to bypass Cloudflare and `requests` for retries.
- **`OpenDotaClient`** (`api/opendota_client.py`) — wraps the OpenDota REST API with a 0.65 s delay between requests, 429 handling, and exponential backoff.
- **`api/queries.py`** — stores all GraphQL query strings.

### `services/`

- Encapsulate business logic.
- Orchestrate API calls and repositories.
- Implement long-running workflows (search, parse, export).
- **`services/discovery/`** — match discovery: `DailyHarvestService` is the only one reachable from the menus; `RampageService`, `TopHeroesService`, and `SpecificTopService` remain as legacy code, wired in `ServiceFactory` but not exposed.
- **`services/analysis_service.py`** — builds the combined rampage ranking (menu `4`) from the parsed replay files, without API calls.
- **`services/drive_service.py`** — the only Google Drive integration: uploads/downloads/deletes the shared `match_ids_*.csv` (menu `1` upload + re-upload, menu `2` download + cleanup). Authenticates as the user via an Installed App OAuth flow. Degrades gracefully when unconfigured.

### `repositories/`

- Thin SQLite wrappers.
- Execute SQL queries and return simple data structures.
- Use `ON CONFLICT` and `RETURNING` clauses (requires modern SQLite).

### `database.py`

- `Database` class manages connection, schema initialization, and migrations.
- Called on every startup via `Database.init()` and `Database.migrate()`.

### `config.py`

- Centralized `Config` class with environment variables and constants.
- Validates that `STRATZ_API_KEY` is present before launching.

### `main.py`

- `main()` initializes the system and starts the main loop.
- Delegates menu handling to `cli/menus.py`.
- Uses `cli/factory.py` for dependency injection.

### `cli/`

- **`cli/factory.py`** — `ServiceFactory` creates wired instances of services and repositories.
- **`cli/menus.py`** — functions `show_*_menu` and `run_*_menu` implement the interactive CLI.

### `core/`

- **`core/time.py`** — shared timestamp parsing (`parse_timestamp`).
- **`core/models.py`** — domain dataclasses (`Hero`, `Match`, `ChatWheel`, etc.).
- **`core/replay_store.py`** — writes and reads the raw OpenDota JSON per match at `data/replays/{match_date}/{match_id}.json`; `match_details` in the database is only an index to these files.

## Design principles

- **Separation of concerns**: each layer has a single responsibility.
- **Incremental growth**: matches are inserted only if they are not already present.
- **Resumable parsing**: match parse state is persisted, so the process can be interrupted and resumed.
- **Rate limiting**: clients respect API delays and back off on 429 responses.
