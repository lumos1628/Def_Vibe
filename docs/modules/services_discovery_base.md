# `services/discovery/base.py` — BaseDiscoveryService

## Purpose

Provides shared infrastructure for hero/player-based match discovery services.

It extracts the common logic of fetching top players and fetching their matches, which was previously duplicated in `TopHeroesService` and `SpecificTopService`.

## Public functions

### `class BaseDiscoveryService`

#### `__init__(client, hero_repository, match_repository)`

Stores the Stratz client, hero repository, and match repository.

#### `_fetch_top_players(hero_id: int, take: int) -> list[int]`

Queries the Stratz leaderboard for the top `take` players of a given hero in the configured bracket.

#### `_fetch_player_matches(player_id: int, hero_id: int, take: int) -> list[dict[str, Any]]`

Queries the recent matches of a player on a specific hero, limited to `take` results.

## Dependencies

- `api.client.StratzClient`
- `api.queries.LEADERBOARD_HERO_QUERY`, `PLAYER_MATCHES_QUERY`
- `config.Config`
- `repositories.hero_repository.HeroRepository`
- `repositories.match_repository.MatchRepository`

## Inputs

- `hero_id` and `take` values.
- Environment: `STRATZ_API_KEY`.

## Outputs

- Lists of Steam account IDs or match dictionaries.

## Usage example

This class is not meant to be used directly. Subclasses inherit from it:

```python
from services.discovery.base import BaseDiscoveryService

class MyDiscoveryService(BaseDiscoveryService):
    def run(self):
        players = self._fetch_top_players(hero_id=86, take=10)
        for player_id in players:
            matches = self._fetch_player_matches(player_id, hero_id=86, take=3)
            print(matches)
```
