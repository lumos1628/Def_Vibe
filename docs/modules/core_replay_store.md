# `core/replay_store.py` — ReplayStore

## Purpose

Stores the raw OpenDota match JSON as one file per match. Files are sharded by match date (UTC) under `data/replays/`:

```
data/replays/2026-08-11/{match_id}.json
```

This keeps SQLite (`match_details`) as a lightweight index instead of a giant blob store.

## Public functions

### `class ReplayStore`

#### `__init__(root: Path = Config.REPLAY_DATA_DIR)`

Sets the root directory for replay files.

#### `match_date(data: dict) -> str`

Returns the match date (`YYYY-MM-DD`, UTC) derived from `start_time`, or `"unknown"` when the timestamp is missing or invalid.

#### `path_for(match_id: int, data: dict) -> Path`

Builds the file path for a match without writing anything.

#### `save(match_id: int, data: dict) -> Path`

Atomically writes the match JSON to disk (via a `.tmp` file that is then renamed) and returns the path.

#### `load(path: Path) -> dict | None`

Loads the match JSON from disk; returns `None` if missing or invalid.

#### `delete(path: Path | None) -> None`

Removes a match file and prunes any empty parent directories.

## Dependencies

- `config.Config` — `REPLAY_DATA_DIR`.
- Standard library: `json`, `datetime`, `pathlib`.

## Inputs

- Full OpenDota match JSON.

## Outputs

- Per-match JSON files under `data/replays/`.

## Usage example

```python
from core.replay_store import ReplayStore

store = ReplayStore()
path = store.save(123456789, match_data)
loaded = store.load(path)
store.delete(path)
```

## Notes

- Writes are atomic (temp file + rename) so a crash never leaves a half-written JSON.
- `MatchRepository.save_match_details()` and `delete_old_matches()` delegate to this class; the `match_details` table only records the `file_path` and `match_date`.
