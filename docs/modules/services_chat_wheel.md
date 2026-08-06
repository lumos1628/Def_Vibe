# `services/chat_wheel_service.py` — ChatWheelService

## Purpose

Loads the local Dota 2 chat wheel catalog (`data/chat_wheel.json`) into the SQLite database. This allows the export service to translate chat wheel IDs into human-readable text.

## Public functions

### `class ChatWheelService`

#### `__init__(repository: ChatWheelRepository)`

Stores the chat wheel repository.

#### `sync() -> int`

Reads `data/chat_wheel.json`, converts it into entries, and upserts them into the database.

#### `ensure_synced() -> None`

Checks if the `chat_wheels` table is empty. If so, calls `sync()`. Otherwise, prints the count of already-synced entries.

## Internal flow

1. `sync()` builds the path `data/chat_wheel.json` relative to the project root.
2. Loads the JSON file.
3. Iterates over each key-value pair, setting `entry["id"] = int(key)`.
4. Calls `ChatWheelRepository.upsert(entries)`.
5. Returns the number of entries inserted.

## Dependencies

- `repositories.chat_wheel_repository.ChatWheelRepository` — persistence layer.
- Standard library: `json`, `pathlib.Path`.

## Inputs

- `data/chat_wheel.json` catalog file.
- `ChatWheelRepository` instance.

## Outputs

- Inserts/updates rows in the `chat_wheels` table.
- Console progress messages.
- Raises `FileNotFoundError` if the catalog is missing.

## Usage example

```python
from database import Database
from repositories.chat_wheel_repository import ChatWheelRepository
from services.chat_wheel_service import ChatWheelService

db = Database()
repo = ChatWheelRepository(db)
service = ChatWheelService(repo)

service.ensure_synced()
```
