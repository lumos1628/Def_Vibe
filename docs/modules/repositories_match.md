# `repositories/match_repository.py` — MatchRepository

## Purpose

Thin SQLite wrapper for match-related data: `rampage_matches`, `match_details`, and `export_log`. It is the largest repository in the project.

## Public functions

### `class MatchRepository`

#### `__init__(db: Database)`

Stores the `Database` instance.

#### `upsert(match_id, hero_id, played_at, steam_account_id) -> bool`

Inserts or updates a discovered match.

Uses `ON CONFLICT(hero_id, match_id)` and `RETURNING id`.

#### `exists_for_hero(match_id, hero_id) -> bool`

Checks whether a `(hero_id, match_id)` pair already exists.

#### `count() -> int`

Returns the total number of matches.

#### `count_distinct() -> int`

Returns the number of distinct `match_id` values.

#### `list_all_match_ids() -> set[int]`

Returns every known `match_id` (any hero). Used by the daily harvest for global dedup.

#### `has_replay_data(opendota_data: dict) -> bool`

Static helper. Returns `True` if the OpenDota data contains a non-empty `kills_log` or `chat` array.

#### `list_unparsed(limit) -> list[int]`

Returns distinct match IDs that need parsing (`parse_status` in `pending`/`queued`/`parsing`, not `unparseable`, no replay data), ordered by `data_verified` and `match_id`.

#### `count_pending_status(match_ids) -> int`

Counts how many of the given `match_id`s still have `parse_status` in `pending`, `queued`, or `parsing` (excluding `unparseable`). Used after a `download_from_csv()` run to decide whether a CSV is fully consumed.

#### `get_parse_state(match_id) -> dict`

Returns the current parse state flags for a match.

#### `mark_data_verified(match_id) -> None`

Sets `data_verified = 1`.

#### `list_queued() -> list[tuple[int, str]]`

Returns `(match_id, parse_job_id)` pairs for queued/parsing jobs.

#### `update_parse_status(match_id, status, job_id) -> None`

Updates `parse_status` and optionally `parse_job_id`.

#### `mark_parse_requested(match_id, job_id) -> None`

Sets the match as queued with the given job ID, increments the request count, and marks it as data-verified.

#### `mark_parsed(match_id, has_replay_data, unparseable) -> None`

Marks the match as done or failed based on the flags.

#### `save_match_details(match_id, opendota_data) -> None`

Writes the full JSON to a per-match file under `data/replays/{match_date}/` via `ReplayStore.save()`, upserts the file index row in `match_details` (`file_path`, `match_date`), and updates `has_replay_data` in `rampage_matches`.

#### `get_match_details(match_id) -> dict | None`

Loads the parsed JSON for a match from its file (`ReplayStore.load()`).

#### `get_hero_ids_for_match(match_id) -> list[int]`

Returns all hero IDs associated with a match.

#### `list_matches_to_export(today_iso) -> list[tuple[int, dict, bool, bool]]`

Returns matches parsed today that have not yet been exported. The query resolves `file_path` from the index and reads each file to build the result.

#### `list_dates_with_parsed() -> list[tuple[str, int]]`

Returns `(played date, distinct match count)` for matches with `parse_status = 'done'` and `has_replay_data = 1`. Used by `AnalysisService` to present the date selection.

#### `list_parsed_rows_by_date(date_prefix=None) -> list[tuple[int, str, int]]`

Returns `(match_id, played_at, hero_id)` rows for matches done with replay data, optionally filtered by a `played_at` date prefix. Used by `AnalysisService` to build the rampage ranking.

#### `list_downloadable(match_ids) -> list[int]`

Returns the input match IDs that still need downloading: excludes matches already `done` with replay data and `unparseable` ones. IDs not present in the database are kept (the JSON is still saved). Order of the input list is preserved.

#### `mark_exported(match_id, exported_at, output_path) -> None`

Records a match in `export_log`.

#### `clear_export_log_for_date(date_str) -> int`

Deletes export log entries for a given date string prefix.

#### `clear_export_log_for_parsed_today(today_iso) -> int`

Deletes export log entries for matches parsed today.

#### `delete_old_matches(days) -> int`

Deletes matches, details, and export logs older than a given number of days. Filtering uses the `match_date` index (no JSON scanning); it also removes the corresponding replay files via `ReplayStore.delete()`, including matches whose date is `unknown`.

## Dependencies

- `database.Database`
- `core.replay_store.ReplayStore`
- Standard library: `datetime`, `sqlite3`, `pathlib`

## Inputs

- Match metadata, OpenDota JSON, parse states, export paths.

## Outputs

- Rows in `rampage_matches`, `match_details`, and `export_log`.

## Usage example

```python
from database import Database
from repositories.match_repository import MatchRepository

db = Database()
repo = MatchRepository(db)

repo.upsert(123456789, 86, "2026-08-01T12:00:00+00:00", 987654321)
print(repo.list_unparsed(limit=10))
```
