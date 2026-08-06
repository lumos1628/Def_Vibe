# `repositories/hero_repository.py` — HeroRepository

## Purpose

Thin SQLite wrapper for the `heroes` table. Handles persistence of the Dota 2 hero catalog.

## Public functions

### `class HeroRepository`

#### `__init__(db: Database)`

Stores the `Database` instance.

#### `upsert(heroes: Iterable[dict]) -> None`

Bulk inserts or updates heroes.

- Maps `displayName` → `display_name` and `shortName` → `short_name`.
- Uses `ON CONFLICT(id) DO UPDATE`.

#### `list_all() -> list[dict]`

Returns all heroes ordered by ID.

#### `count() -> int`

Returns the number of heroes. Delegates to `Database.count_heroes()`.

## Internal flow

- `upsert()` builds rows of `(id, display_name, short_name, synced_at)` and uses `executemany()`.
- `list_all()` enables `sqlite3.Row` factory for dict-like access.

## Dependencies

- `database.Database`
- Standard library: `datetime`, `sqlite3`

## Inputs

- Iterable of hero dictionaries from the Stratz API.
- `Database` instance.

## Outputs

- Rows in the `heroes` table.

## Usage example

```python
from database import Database
from repositories.hero_repository import HeroRepository

db = Database()
repo = HeroRepository(db)

heroes = [
    {"id": 1, "displayName": "Anti-Mage", "shortName": "antimage"},
]
repo.upsert(heroes)
print(repo.list_all())
```
