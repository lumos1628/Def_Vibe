# `api/queries.py` — GraphQL Queries

## Purpose

Centralizes all GraphQL query strings used by the application. This prevents query strings from being duplicated or hardcoded inside services.

## Public functions

This module does not define functions or classes. It exports string constants.

## Exported constants

| Constant | Variables | Description |
|----------|-----------|-------------|
| `HEROES_QUERY` | None | Fetches the full hero catalog: `id`, `displayName`, `shortName`. |
| `RAMPAGES_QUERY` | `heroId`, `bracketBasicIds`, `take` | Fetches rampage matches for a hero and bracket. |
| `LATEST_RAMPAGES_QUERY` | `heroId`, `take` | Fetches the latest rampage matches for a hero. |
| `MATCH_DATE_QUERY` | `matchId` | Fetches the start date/time of a match. |
| `HERO_STATS_WIN_WEEK_QUERY` | `bracketIds` | Fetches weekly win/played stats per hero. |
| `LEADERBOARD_HERO_QUERY` | `heroIds`, `bracketIds`, `take` | Fetches top players for a hero. |
| `PLAYER_MATCHES_QUERY` | `steamAccountId`, `heroIds`, `take` | Fetches recent matches of a player on a specific hero. |
| `RECENT_RAMPAGES_QUERY` | `heroId`, `take` | Fetches recent rampages with the nested `match.startDateTime` inlined (max `take` is 20). |
| `PRO_PLAYERS_QUERY` | None | Fetches all pro player accounts (`id`, `name`). |
| `PRO_RECENT_MATCHES_QUERY` | `steamAccountIds`, `startDateTime`, `take` | Fetches recent matches for up to 5 players per call, including `players { steamAccountId heroId }` to resolve the played hero. |
| `PLAYERS_HERO_MATCHES_QUERY` | `steamAccountIds`, `startDateTime`, `heroIds`, `take` | Fetches recent matches for up to 5 players per call filtered by hero. |

## Internal flow

- Each constant is a plain string containing a valid GraphQL query.
- Services import the query and pass it to `StratzClient.execute()` along with the required variables.

## Dependencies

- None. This is a constants-only module.

## Inputs

- No runtime inputs.

## Outputs

- GraphQL query strings consumed by `StratzClient.execute()`.

## Usage example

```python
from api.client import StratzClient
from api.queries import HEROES_QUERY, MATCH_DATE_QUERY

client = StratzClient()

heroes = client.execute(HEROES_QUERY)
print(heroes["constants"]["heroes"])

match_date = client.execute(MATCH_DATE_QUERY, {"matchId": 123456789})
print(match_date["match"]["startDateTime"])

client.pause()
```

## Rules for adding queries

- Define new query strings in this file.
- Call them through `StratzClient.execute()`.
- Do not hardcode GraphQL strings anywhere else.
