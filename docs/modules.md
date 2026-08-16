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
- `DailyHarvestService`
- `ParseService`
- `ExportService`
- `AnalysisService`
- `DriveService`

## `cli/menus.py`

**Responsibility:** Interactive CLI menus.

- `show_main_menu()`, `show_search_menu()`, `show_parse_menu()`, `show_export_menu()`, `show_analysis_menu()` — display menus.
- `run_search_menu()`, `run_parse_menu()`, `run_export_menu()`, `run_analysis_menu()` — dispatch user choices to services.
- `_pick_match_ids_csv()` — picks a `match_ids_*.csv` locally; when none exist and Drive is configured, offers to download the most recent one from Google Drive.

## `config.py`

**Responsibility:** Centralized configuration and environment validation.

**Class:** `Config`
- Loads `.env` with `python-dotenv`.
- Exposes API keys, base URLs, database/export paths, delays, batch sizes, hero-specific search parameters, and Google Drive settings (`GOOGLE_DRIVE_CLIENT_SECRETS`, `GOOGLE_DRIVE_TOKEN_PATH`, `GOOGLE_DRIVE_FOLDER_ID`).
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
- `RECENT_RAMPAGES_QUERY`
- `PRO_PLAYERS_QUERY`
- `PRO_RECENT_MATCHES_QUERY`
- `PLAYERS_HERO_MATCHES_QUERY`

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

## `core/replay_store.py`

**Responsibility:** Raw replay JSON file storage.

**Class:** `ReplayStore`
- `save(match_date, match_id, data)` — writes `data/replays/{match_date}/{match_id}.json`.
- `load(match_date, match_id)` — reads the JSON back.
- `delete(match_date, match_id)` — removes the file.
- Used by `MatchRepository` for all replay data; the `match_details` table only indexes these files.

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

## `services/discovery/daily_harvest_service.py`

**Class:** `DailyHarvestService(BaseDiscoveryService)`
- `harvest()` — collects new match IDs (target `Config.DAILY_MATCH_TARGET`, max age `Config.DAILY_MATCH_MAX_AGE_DAYS`) in priority phases: recent rampages, pro player matches, unique-mechanics heroes, most-played heroes, highest-winrate heroes. Stops when the target is reached.
- `_phase_rampages()` — latest 20 rampages per hero (all brackets), dates inlined via nested `match`.
- `_phase_pro_players()` — recent matches of pro players, batched 5 accounts per request.
- `_phase_hero_leaderboards()` — top leaderboard players per hero, batched recent matches on that hero.
- `_fetch_patch_hero_rankings()` — most-played and highest-winrate heroes from `winWeek`.
- Global dedup: skips any `match_id` already present in `rampage_matches` (any hero).

## `services/parse_service.py`

**Class:** `ParseService`
- Constructor receives `client`, `match_repository`, and an optional `drive_service` (used by the Drive download/cleanup helpers).
- `parse_unparsed()` — main parse loop.
- `_enqueue_unparsed()` — verifies matches and requests parses.
- `_poll_jobs()` — polls OpenDota job statuses.
- `_fetch_done_matches()` — retries fetching parsed data.
- `_is_replay_available()`, `_is_job_done()`, `_handle_rate_limit()` — helpers.
- `clean_old_matches()` — deletes old records.
- `list_match_ids_csvs()` — available `match_ids_*.csv` exports.
- `enqueue_from_csv()` — enqueues parses for CSV IDs (Tecsup), writes `parse_jobs_*.csv`.
- `download_from_csv()` — downloads/saves parsed matches from CSV (home).
- `download_latest_match_ids_from_drive()` — downloads the most recent `match_ids_*.csv` from Drive to `exports/`.
- `count_pending_for_csv()` — how many IDs in a CSV are still pending/queued/parsing.
- `cleanup_consumed_csv()` — deletes a fully processed `match_ids_*.csv` locally and on Drive.

## `services/drive_service.py`

**Class:** `DriveService`
- Thin wrapper around the Google Drive API v3, authenticating as the user via an Installed App OAuth flow (client secret + locally saved token).
- `enabled` — True when the API service was built (client secrets + token + folder ID configured).
- `upload(path)` — creates or overwrites a file by name in the shared folder.
- `download(remote_name, dest)` — downloads a file by name to a local path.
- `delete(remote_name)` — deletes a file by name.
- `list_files()` — names of files in the shared folder.
- All methods degrade gracefully (Spanish message, no exception propagation) so the app works without Drive.

## `services/export_service.py`

**Class:** `ExportService`
- Constructor receives `hero_repository`, `match_repository`, `chat_wheel_repository`, and an optional `drive_service` (used only by `export_match_ids_csv()`).
- `export_chat_kills()` — main export logic.
- `export_chat_kills_csv()` — convenience wrapper.
- `reexport_parsed_today()` — clears today's log and re-exports.
- `export_match_ids_csv()` — writes `exports/match_ids_YYYY-MM-DD.csv` from saved match IDs and uploads it to Drive (when configured).
- `_build_chat_rows()`, `_build_kill_rows()` — build CSV rows.
- `_detect_rampage()` — finds 5 kills within 18 seconds.
- `_resolve_chat_message()` — resolves chat wheel IDs.
- `_write_csv()`, `_write_excel()`, `_style_sheet()` — output formatting.

## `services/analysis_service.py`

**Class:** `AnalysisService`
- `list_dates()` — parsed dates with distinct match counts.
- `export_top()` — builds a combined rampage ranking for a date (or all dates) from parsed match files and writes the CSV to `exports/rampages/`.
- `_build_records()`, `_detect_shortest_rampage()` — per-match rampage detection (shortest 5-kill window ≤18s).
- `_collect_reactions()`, `_resolve_chat_message()` — reactions after the rampage and chat wheel resolution.
- `_rank_records()` — rank-based scoring (speed + reactions) within the selection.
- `_print_top()`, `_write_csv()` — console output and CSV writing.

## `repositories/hero_repository.py`

**Class:** `HeroRepository`
- `upsert()` — bulk insert/update heroes.
- `list_all()` — returns all heroes.
- `count()` — delegates to `Database.count_heroes()`.

## `repositories/match_repository.py`

**Class:** `MatchRepository`
- `upsert()`, `exists_for_hero()`, `count()` — basic match CRUD.
- `count_distinct()`, `list_all_match_ids()` — global `match_id` counting and lookup used by the daily harvest dedup.
- `has_replay_data()` — checks if OpenDota data contains chat or kills log.
- `list_unparsed()`, `count_pending_status()`, `list_queued()`, `get_parse_state()` — parse workflow queries.
- `mark_data_verified()`, `update_parse_status()`, `mark_parse_requested()`, `mark_parsed()` — state transitions.
- `save_match_details()`, `get_match_details()` — raw JSON storage in per-match files via `core/replay_store.ReplayStore` (SQLite keeps only the file index).
- `get_hero_ids_for_match()` — returns heroes associated with a match.
- `list_dates_with_parsed()`, `list_parsed_rows_by_date()` — parsed match queries used by `AnalysisService`.
- `list_matches_to_export()`, `mark_exported()`, `clear_export_log_for_date()`, `clear_export_log_for_parsed_today()` — export tracking.
- `delete_old_matches()` — cleanup.

## `repositories/chat_wheel_repository.py`

**Class:** `ChatWheelRepository`
- `upsert()` — bulk insert/update chat wheels.
- `get_by_id()` — lookup for export resolution.
- `count()`.
