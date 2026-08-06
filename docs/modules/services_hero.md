# `services/hero_service.py` — HeroService

## Purpose

Synchronizes the local hero catalog from the Stratz API. The catalog is needed to map hero IDs to names and to iterate over all heroes during rampage searches.

## Public functions

### `class HeroService`

#### `__init__(client: StratzClient, repository: HeroRepository)`

Stores the API client and the hero repository.

#### `sync() -> int`

Fetches the full hero list from Stratz and stores it in the database.

- Prints progress in Spanish.
- Returns the number of heroes synchronized.

#### `ensure_synced() -> None`

Checks if the hero table is empty. If so, calls `sync()`. Otherwise, prints the count of already-synced heroes.

## Internal flow

1. `sync()` calls `StratzClient.execute(HEROES_QUERY)`.
2. Extracts `data["constants"]["heroes"]`.
3. Calls `HeroRepository.upsert(heroes)` to store the list.
4. `ensure_synced()` uses `HeroRepository.count()` to decide whether to sync.

## Dependencies

- `api.client.StratzClient` — GraphQL client.
- `api.queries.HEROES_QUERY` — hero catalog query.
- `repositories.hero_repository.HeroRepository` — persistence layer.

## Inputs

- `StratzClient` instance.
- `HeroRepository` instance.
- Environment: `STRATZ_API_KEY` via `StratzClient`.

## Outputs

- Inserts/updates rows in the `heroes` table.
- Console progress messages.

## Usage example

```python
from api.client import StratzClient
from database import Database
from repositories.hero_repository import HeroRepository
from services.hero_service import HeroService

db = Database()
client = StratzClient()
repo = HeroRepository(db)
service = HeroService(client, repo)

service.ensure_synced()
```
