# `services/discovery/daily_harvest_service.py` — DailyHarvestService

## Purpose

Collects a daily batch of new match IDs, targeting `Config.DAILY_MATCH_TARGET` (2900 by default) distinct `match_id` values that are:

- Not already stored in `rampage_matches` (global dedup across all heroes, so IDs are always distinct from previous days).
- At most `Config.DAILY_MATCH_MAX_AGE_DAYS` days old (7 by default).

Phases run in priority order and each one stops as soon as the target is reached. Inherits shared discovery helpers from `BaseDiscoveryService`.

## Public functions

### `class DailyHarvestService(BaseDiscoveryService)`

#### `__init__(client, hero_repository, match_repository)`

Stores the Stratz client, hero repository, and match repository, and initializes the run state (known IDs, saved IDs, cutoff timestamp).

#### `harvest() -> list[int]`

Runs the harvest and returns the sorted list of new distinct `match_id`s saved during the run:

1. Loads every known `match_id` from the database into memory.
2. Phase 1: recent rampages for every hero (all brackets).
3. Phase 2 (if short of target): recent matches of pro players.
4. Phase 3 (if short): top leaderboard players of the unique-mechanics heroes (`Config.SPECIFIC_TOP_HEROES`).
5. Phase 4 (if short): top players of the most-played heroes of the patch.
6. Phase 5 (if short): top players of the highest-winrate heroes.

## Internal flow

1. `_phase_rampages()` — calls `RECENT_RAMPAGES_QUERY` per hero (`take` max 20, enforced by Stratz). The rampage entries inline `match.startDateTime`, so no extra date queries are needed. Entries older than the cutoff are skipped client-side.
2. `_phase_pro_players()` — fetches `PRO_PLAYERS_QUERY` (pro accounts), then batches up to `PLAYERS_BATCH_SIZE` (5, Stratz max) accounts per `PRO_RECENT_MATCHES_QUERY` call. The played hero is resolved from `match.players` via `_resolve_player_hero()`.
3. `_phase_hero_leaderboards(hero_ids, leaderboard_take, label)` — fetches top players per hero with the inherited `_fetch_top_players()`, then batches their recent matches on that hero via `PLAYERS_HERO_MATCHES_QUERY` through `_harvest_player_batches()`.
4. `_fetch_patch_hero_rankings()` — aggregates `HERO_STATS_WIN_WEEK_QUERY` into a most-played ranking and a winrate ranking (minimum `Config.WINRATE_MIN_MATCHES` weekly matches to reduce noise).
5. `_try_save()` — skips matches already known or already saved this run, then upserts. Only distinct `match_id` values count toward the target.

## Dependencies

- `api.client.StratzClient`
- `api.queries` — `RECENT_RAMPAGES_QUERY`, `PRO_PLAYERS_QUERY`, `PRO_RECENT_MATCHES_QUERY`, `PLAYERS_HERO_MATCHES_QUERY`, `HERO_STATS_WIN_WEEK_QUERY`
- `services.discovery.base.BaseDiscoveryService`
- `core.time.parse_timestamp`
- `repositories.hero_repository.HeroRepository`
- `repositories.match_repository.MatchRepository`
- `config.Config`

## Inputs

- Hero list from the database.
- `Config.DAILY_*`, `Config.PLAYERS_BATCH_SIZE`, `Config.PLAYER_RECENT_MATCHES_TAKE`, `Config.PRO_PLAYERS_LIMIT`, `Config.RELEVANT_HERO_LEADERBOARD_TAKE`, `Config.TOP_HERO_LEADERBOARD_TAKE`, `Config.WINRATE_MIN_MATCHES`, `Config.SPECIFIC_TOP_HEROES`, `Config.HERO_STATS_BRACKETS`.

## Outputs

- Inserts rows in `rampage_matches`.
- Console progress messages per phase and a final summary.
- Returns the sorted list of new distinct match IDs saved during the run.

## Usage example

```python
from api.client import StratzClient
from database import Database
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository
from services.discovery.daily_harvest_service import DailyHarvestService

db = Database()
client = StratzClient()
service = DailyHarvestService(client, HeroRepository(db), MatchRepository(db))
saved = service.harvest()
print(f"Saved {len(saved)} new match IDs")
```
