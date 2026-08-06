# `services/discovery/specific_top_service.py` — SpecificTopService

## Purpose

Similar to `TopHeroesService`, but focused on a configured list of heroes with custom top-player counts. This allows targeted discovery for heroes of special interest.

Inherits shared discovery helpers from `BaseDiscoveryService`.

## Public functions

### `class SpecificTopService(BaseDiscoveryService)`

#### `__init__(client, hero_repository, match_repository)`

Stores the Stratz client, hero repository, and match repository.

#### `fetch_specific_top_matches() -> int`

For each hero in `Config.SPECIFIC_TOP_HEROES`:

1. Fetches the configured number of top players.
2. For each player, fetches their latest matches on that hero.
3. Saves new matches to `rampage_matches`.

Returns the total number of new matches saved.

## Internal flow

1. Load the hero list from the database.
2. Iterate over `Config.SPECIFIC_TOP_HEROES` (e.g., Rubick: 50, Invoker: 25, Morphling: 25, etc.).
3. For each hero, call inherited `_fetch_top_players(hero_id, top_count)`.
4. For each player, call inherited `_fetch_player_matches(player_id, hero_id, take)`.
5. Skip duplicates via `MatchRepository.exists_for_hero()`.
6. Call `StratzClient.pause()` after each player and each hero.

## Dependencies

- `api.client.StratzClient`
- `services.discovery.base.BaseDiscoveryService`
- `core.time.parse_timestamp`
- `repositories.hero_repository.HeroRepository`
- `repositories.match_repository.MatchRepository`
- `config.Config`

## Inputs

- Hero list from the database.
- `Config.SPECIFIC_TOP_HEROES` mapping: `{hero_id: top_count}`.
- `Config.SPECIFIC_TOP_MATCHES_PER_PLAYER`.

## Outputs

- Inserts/updates rows in `rampage_matches`.
- Console progress messages.
- Returns total saved count.

## Usage example

```python
from api.client import StratzClient
from database import Database
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository
from services.discovery.specific_top_service import SpecificTopService

db = Database()
client = StratzClient()
hero_repo = HeroRepository(db)
match_repo = MatchRepository(db)

service = SpecificTopService(client, hero_repo, match_repo)
total = service.fetch_specific_top_matches()
print(f"Saved {total} matches")
```
