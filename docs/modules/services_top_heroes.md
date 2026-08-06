# `services/discovery/top_heroes_service.py` — TopHeroesService

## Purpose

Discovers matches by combining the most-played heroes with the top players for each hero. This provides a broader set of high-skill matches without relying solely on the rampage filter.

Inherits shared discovery helpers from `BaseDiscoveryService`.

## Public functions

### `class TopHeroesService(BaseDiscoveryService)`

#### `__init__(client, hero_repository, match_repository)`

Stores the Stratz client, hero repository, and match repository.

#### `fetch_top_heroes_matches() -> int`

Main workflow:

1. Finds the top 60 most-played heroes.
2. For each hero, finds the top 3 players.
3. For each player, fetches the 3 most recent matches on that hero.
4. Saves new matches to `rampage_matches`.

Returns the total number of new matches saved.

## Internal flow

1. `_fetch_top_heroes(heroes)` calls `HERO_STATS_WIN_WEEK_QUERY` and aggregates `matchCount` per hero. Returns the top 60.
2. Inherits `_fetch_top_players(hero_id, take)` from `BaseDiscoveryService`.
3. Inherits `_fetch_player_matches(player_id, hero_id, take)` from `BaseDiscoveryService`.
4. For each match, `core.time.parse_timestamp()` normalizes the start time.
5. Duplicates are skipped using `MatchRepository.exists_for_hero()`.
6. `StratzClient.pause()` is called after each player and after each hero.

## Dependencies

- `api.client.StratzClient`
- `api.queries.HERO_STATS_WIN_WEEK_QUERY`
- `services.discovery.base.BaseDiscoveryService`
- `core.time.parse_timestamp`
- `repositories.hero_repository.HeroRepository`
- `repositories.match_repository.MatchRepository`
- `config.Config`

## Inputs

- Hero list from the database.
- Config constants: `TOP_HEROES_COUNT`, `TOP_PLAYERS_PER_HERO`, `TOP_MATCHES_PER_PLAYER`, `LEADERBOARD_BRACKET`, `HERO_STATS_BRACKETS`.

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
from services.discovery.top_heroes_service import TopHeroesService

db = Database()
client = StratzClient()
hero_repo = HeroRepository(db)
match_repo = MatchRepository(db)

service = TopHeroesService(client, hero_repo, match_repo)
total = service.fetch_top_heroes_matches()
print(f"Saved {total} matches")
```
