# `database.py` — Database

## Purpose

Manages the SQLite database connection, schema initialization, and schema migrations. It is the lowest layer of the persistence stack.

## Public functions

### `class Database`

#### `__init__(db_path: Path = Config.DB_PATH)`

Stores the database file path.

#### `get_connection() -> sqlite3.Connection`

Returns a connection to the SQLite database.

#### `init() -> None`

Creates the initial schema if it does not exist.

Tables created:

- `heroes`
- `rampage_matches`
- `export_log`
- `chat_wheels`

Indexes created:

- `idx_rampage_hero` on `rampage_matches(hero_id)`

#### `migrate() -> None`

Upgrades existing databases by:

- Adding missing columns to `rampage_matches`.
- Creating the `match_details` table.
- Adding missing indexes.
- Backfilling `has_replay_data`, `parse_status`, and `data_verified`.
- Resetting `unparseable` for recent matches so they can be retried.
- Adding `short_name` to `heroes` if missing.

#### `table_exists(name: str) -> bool`

Helper that checks if a table exists in `sqlite_master`.

#### `count_heroes() -> int`

Returns the number of heroes. Used by `HeroRepository`.

## Dependencies

- `config.Config`
- Standard library: `datetime`, `json`, `sqlite3`, `pathlib`

## Inputs

- Database path (default `data.db`).
- Existing SQLite file (if any).

## Outputs

- SQLite file with current schema.

## Usage example

```python
from database import Database

db = Database()
db.init()
db.migrate()

with db.get_connection() as conn:
    cursor = conn.execute("SELECT COUNT(*) FROM heroes")
    print(cursor.fetchone()[0])
```

## Migration notes

`Database.init()` and `Database.migrate()` must be called on every startup. `init()` is safe to run repeatedly because it uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`.
