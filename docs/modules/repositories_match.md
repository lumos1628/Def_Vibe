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

#### `has_replay_data(opendota_data: dict) -> bool`

Static helper. Returns `True` if the OpenDota data contains a non-empty `kills_log` or `chat` array.

#### `list_unparsed(limit) -> list[int]`

Returns match IDs that need parsing, ordered by `data_verified` and `match_id`.

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

Inserts/updates the full JSON in `match_details` and updates `has_replay_data` in `rampage_matches`.

#### `get_match_details(match_id) -> dict | None`

Returns the parsed JSON for a match.

#### `get_hero_ids_for_match(match_id) -> list[int]`

Returns all hero IDs associated with a match.

#### `list_matches_to_export(today_iso) -> list[tuple[int, dict, bool, bool]]`

Returns matches parsed today that have not yet been exported.

#### `mark_exported(match_id, exported_at, output_path) -> None`

Records a match in `export_log`.

#### `clear_export_log_for_date(date_str) -> int`

Deletes export log entries for a given date string prefix.

#### `clear_export_log_for_parsed_today(today_iso) -> int`

Deletes export log entries for matches parsed today.

#### `delete_old_matches(days) -> int`

Deletes matches, details, and export logs older than a given number of days.

## Dependencies

- `database.Database`
- Standard library: `datetime`, `json`, `sqlite3`

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
