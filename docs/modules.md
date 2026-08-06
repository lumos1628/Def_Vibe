# Modules

## `main.py`

**Responsibility:** Entry point and orchestration.

**Main functions:**
- `main()` — validates config, initializes the database, syncs catalogs, and runs the main loop.

## `cli/factory.py`

**Responsibility:** Dependency injection container (`ServiceFactory`).

Creates wired instances of all services, repositories, clients, and the database.

**Services created:**
- `HeroService`
- `ChatWheelService`
- `RampageService`
- `TopHeroesService`
- `SpecificTopService`
- `ParseService`
- `ExportService`

## `cli/menus.py`

**Responsibility:** Interactive CLI menus.

- `show_main_menu()`, `show_search_menu()`, `show_parse_menu()`, `show_export_menu()` — display menus.
- `run_search_menu()`, `run_parse_menu()`, `run_export_menu()` — dispatch user choices to services.

## `config.py`

**Responsibility:** Centralized configuration and environment validation.

**Class:** `Config`
- Loads `.env` with `python-dotenv`.
- Exposes API keys, base URLs, database/export paths, delays, batch sizes, and hero-specific search parameters.
- `validate()` raises `ValueError` if `STRATZ_API_KEY` is missing.

## `database.py`

**Responsibility:** SQLite connection management, schema initialization, and migrations.

**Class:** `Database`
- `get_connection()` — returns a `sqlite3.Connection`.
- `init()` — creates the initial schema (`heroes`, `rampage_matches`, `export_log`, `chat_wheels`).
- `migrate()` — upgrades existing databases with new columns, tables, and indexes.
- `table_exists()` — helper for migration checks.
- `count_heroes()` — helper used by `HeroRepository`.

## `api/client.py`

**Responsibility:** Stratz GraphQL API client.

**Class:** `StratzClient`
- Builds `Authorization: Bearer {STRATZ_API_KEY}` headers.
- Uses `cloudscraper` to bypass Cloudflare.
- Retries failed requests with exponential backoff.
- `execute(query, variables)` returns the `data` portion of the JSON response.
- Raises `StratzApiError` on GraphQL errors.

## `api/opendota_client.py`

**Responsibility:** OpenDota REST API client.

**Class:** `OpenDotaClient`
- `requests.Session` for connection reuse.
- Adds optional `api_key` query parameter.
- Handles 429 rate limits with `Retry-After` and exponential backoff.
- Raises `RateLimitError` after too many consecutive 429s.
- Methods:
  - `get_match(match_id)`
  - `request_parse(match_id)`
  - `get_request_status(job_id)`

## `api/queries.py`

**Responsibility:** GraphQL query strings.

**Queries:**
- `HEROES_QUERY`
- `RAMPAGES_QUERY`
- `LATEST_RAMPAGES_QUERY`
- `MATCH_DATE_QUERY`
- `HERO_STATS_WIN_WEEK_QUERY`
- `LEADERBOARD_HERO_QUERY`
- `PLAYER_MATCHES_QUERY`

## `services/hero_service.py`

**Class:** `HeroService`
- `sync()` — fetches heroes from Stratz and stores them.
- `ensure_synced()` — syncs only if the table is empty.

## `services/chat_wheel_service.py`

**Class:** `ChatWheelService`
- `sync()` — loads `data/chat_wheel.json` and stores entries.
- `ensure_synced()` — syncs only if the table is empty.

## `core/time.py`

**Responsibility:** Shared timestamp parsing utility.

- `parse_timestamp(value)` — normalizes strings, ints, and floats into ISO 8601 UTC strings.

## `core/models.py`

**Responsibility:** Domain dataclasses.

- `Hero`, `ChatWheel`, `Match`, `OpenDotaMatchData`, `ExportRecord`.

## `services/discovery/base.py`

**Class:** `BaseDiscoveryService`
- Shared infrastructure for top-player/match discovery.
- `_fetch_top_players(hero_id, take)` — queries the leaderboard.
- `_fetch_player_matches(player_id, hero_id, take)` — queries player matches.

## `services/discovery/rampage_service.py`

**Class:** `RampageService`
- `fetch_by_rampages()` — rampages in the `DIVINE_IMMORTAL` bracket.
- `fetch_latest_rampages()` — latest 5 rampages per hero.
- `_run_rampage_search()` — shared implementation.
- `_fetch_match_date()` — resolves match start time via `MATCH_DATE_QUERY`.

## `services/discovery/top_heroes_service.py`

**Class:** `TopHeroesService(BaseDiscoveryService)`
- `fetch_top_heroes_matches()` — finds the top 60 heroes, top 3 players per hero, and 3 matches per player.
- `_fetch_top_heroes()` — determines the most-played heroes.
- Inherits `_fetch_top_players()` and `_fetch_player_matches()` from `BaseDiscoveryService`.

## `services/discovery/specific_top_service.py`

**Class:** `SpecificTopService(BaseDiscoveryService)`
- `fetch_specific_top_matches()` — searches top players for configured heroes from `Config.SPECIFIC_TOP_HEROES`.
- Inherits shared discovery helpers from `BaseDiscoveryService`.

## `services/parse_service.py`

**Class:** `ParseService`
- `parse_unparsed()` — main parse loop.
- `_enqueue_unparsed()` — verifies matches and requests parses.
- `_poll_jobs()` — polls OpenDota job statuses.
- `_fetch_done_matches()` — retries fetching parsed data.
- `_is_replay_available()`, `_is_job_done()`, `_handle_rate_limit()` — helpers.
- `clean_old_matches()` — deletes old records.

## `services/export_service.py`

**Class:** `ExportService`
- `export_chat_kills()` — main export logic.
- `export_chat_kills_csv()` — convenience wrapper.
- `reexport_parsed_today()` — clears today's log and re-exports.
- `_build_chat_rows()`, `_build_kill_rows()` — build CSV rows.
- `_detect_rampage()` — finds 5 kills within 18 seconds.
- `_resolve_chat_message()` — resolves chat wheel IDs.
- `_write_csv()`, `_write_excel()`, `_style_sheet()` — output formatting.

## `repositories/hero_repository.py`

**Class:** `HeroRepository`
- `upsert()` — bulk insert/update heroes.
- `list_all()` — returns all heroes.
- `count()` — delegates to `Database.count_heroes()`.

## `repositories/match_repository.py`

**Class:** `MatchRepository`
- `upsert()`, `exists_for_hero()`, `count()` — basic match CRUD.
- `has_replay_data()` — checks if OpenDota data contains chat or kills log.
- `list_unparsed()`, `list_queued()`, `get_parse_state()` — parse workflow queries.
- `mark_data_verified()`, `update_parse_status()`, `mark_parse_requested()`, `mark_parsed()` — state transitions.
- `save_match_details()`, `get_match_details()` — JSON storage.
- `get_hero_ids_for_match()` — returns heroes associated with a match.
- `list_matches_to_export()`, `mark_exported()`, `clear_export_log_for_date()`, `clear_export_log_for_parsed_today()` — export tracking.
- `delete_old_matches()` — cleanup.

## `repositories/chat_wheel_repository.py`

**Class:** `ChatWheelRepository`
- `upsert()` — bulk insert/update chat wheels.
- `get_by_id()` — lookup for export resolution.
- `count()`.
