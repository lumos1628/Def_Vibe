# `services/discovery/rampage_service.py` — RampageService

## Purpose

Discovers Dota 2 matches that contain rampages for a given hero. Supports both bracket-filtered and unfiltered searches.

## Public functions

### `class RampageService`

#### `__init__(client, hero_repository, match_repository)`

Stores the Stratz client, hero repository, and match repository.

#### `fetch_by_rampages() -> int`

Searches rampage matches in the `DIVINE_IMMORTAL` bracket, taking `Config.RAMPAGE_TAKE` matches per hero.

Returns the number of new matches saved.

#### `fetch_latest_rampages() -> int`

Searches the latest 5 rampage matches per hero, regardless of bracket.

Returns the number of new matches saved.

## Internal flow

Both public methods delegate to `_run_rampage_search()`:

1. Load the full hero list from `HeroRepository`.
2. For each hero, call the appropriate GraphQL query.
3. For each returned match:
   - Check if `(hero_id, match_id)` already exists; if so, skip.
   - Fetch the match date using `MATCH_DATE_QUERY`.
   - Upsert the match into `rampage_matches`.
4. After each hero, call `StratzClient.pause()` to respect rate limits.

### `_fetch_match_date(match_id)`

Queries the Stratz API for the match start time. Falls back to the current UTC time if the API does not return a date. Uses `core.time.parse_timestamp()` to normalize the value.

## Dependencies

- `api.client.StratzClient`
- `api.queries.LATEST_RAMPAGES_QUERY`, `MATCH_DATE_QUERY`, `RAMPAGES_QUERY`
- `core.time.parse_timestamp`
- `repositories.hero_repository.HeroRepository`
- `repositories.match_repository.MatchRepository`
- `config.Config`

## Inputs

- Hero list from the database.
- GraphQL query and bracket/take parameters.
- Environment: `STRATZ_API_KEY`.

## Outputs

- Inserts/updates rows in `rampage_matches`.
- Console progress messages per hero/match.
- Returns total saved count.

## Usage example

```python
from api.client import StratzClient
from database import Database
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository
from services.discovery.rampage_service import RampageService

db = Database()
client = StratzClient()
hero_repo = HeroRepository(db)
match_repo = MatchRepository(db)

service = RampageService(client, hero_repo, match_repo)
total = service.fetch_by_rampages()
print(f"Saved {total} matches")
```
