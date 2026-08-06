# `repositories/chat_wheel_repository.py` — ChatWheelRepository

## Purpose

Thin SQLite wrapper for the `chat_wheels` table. Enables lookup of chat wheel messages by ID during export.

## Public functions

### `class ChatWheelRepository`

#### `__init__(db: Database)`

Stores the `Database` instance.

#### `upsert(entries: Iterable[dict]) -> None`

Bulk inserts or updates chat wheel entries.

- Maps `all_chat` to `0`/`1` integer.
- Uses `ON CONFLICT(id) DO UPDATE`.

#### `get_by_id(chat_wheel_id: int) -> dict | None`

Returns a chat wheel entry by ID, or `None` if not found.

#### `count() -> int`

Returns the number of chat wheel entries.

## Dependencies

- `database.Database`
- Standard library: `datetime`, `sqlite3`

## Inputs

- Chat wheel entries from `data/chat_wheel.json`.

## Outputs

- Rows in the `chat_wheels` table.

## Usage example

```python
from database import Database
from repositories.chat_wheel_repository import ChatWheelRepository

db = Database()
repo = ChatWheelRepository(db)

entry = repo.get_by_id(7)
print(entry)
```
