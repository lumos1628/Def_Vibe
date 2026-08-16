# `config.py` — Config

## Purpose

Centralizes all configuration: environment variables, API URLs, database paths, delays, batch sizes, and feature-specific constants. It also validates that the required API key is present.

## Public functions

### `class Config`

Container class with class-level constants. No instances are created.

#### `validate() -> None`

Raises `ValueError` if `STRATZ_API_KEY` is missing.

## Key constants

| Constant | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `STRATZ_API_KEY` env | Stratz API bearer token |
| `OPENDOTA_API_KEY` | `OPENDOTA_API_KEY` env | Optional OpenDota API key |
| `BASE_URL` | `https://api.stratz.com/graphql` | Stratz GraphQL endpoint |
| `OPENDOTA_BASE_URL` | `https://api.opendota.com/api` | OpenDota REST endpoint |
| `DB_PATH` | `Path("data.db")` | SQLite database path |
| `REPLAY_DATA_DIR` | `Path("data/replays")` | Per-match replay JSON files, sharded by date |
| `EXPORT_DIR` | `Path("exports")` | Export output directory |
| `ANALYSIS_EXPORT_DIR` | `Path("exports/rampages")` | Rampage ranking output directory |
| `GOOGLE_DRIVE_CLIENT_SECRETS` | env (optional) | Path to the Drive OAuth Desktop-app client secret JSON (e.g. `data/drive_client_secret.json`) |
| `GOOGLE_DRIVE_TOKEN_PATH` | env (optional) | Where the OAuth token is saved (default `data/drive_token.json`) |
| `GOOGLE_DRIVE_FOLDER_ID` | env (optional) | Drive folder that hosts the `match_ids_*.csv` |
| `BRACKET` | `DIVINE_IMMORTAL` | Default ranked bracket (legacy services) |
| `REQUEST_DELAY` | `0.5` | Delay between Stratz requests |
| `OPENDOTA_REQUEST_DELAY` | `0.65` | Delay between OpenDota requests |
| `MAX_RETRIES` | `3` | Retry attempts for Stratz requests |
| `RAMPAGE_TAKE` | `2` | Rampage matches per hero per run (legacy) |
| `MAX_REPLAY_AGE_DAYS` | `8` | Max replay age before marking unparseable |
| `CLEAN_OLD_MATCHES_DAYS` | `7` | Default cleanup window |
| `PARSE_BATCH_SIZE` | `3000` | Matches parsed per batch |
| `PARSE_POLL_INTERVAL` | `150` | Seconds between parse polls |
| `PARSE_MAX_POLLS` | `4` | Max poll rounds |
| `PARSE_MAX_RETRIES` | `3` | Retries per parse request |
| `OPENDOTA_POLL_DELAY` | `1.0` | Seconds between job status polls |
| `PARSE_GET_ONLY` | `True` | GET-only parse mode: no parse jobs are enqueued or polled |
| `RATE_LIMIT_MAX_RETRIES` | `10` | Consecutive 429s before pausing |
| `RATE_LIMIT_PAUSE_SECONDS` | `300` | Pause on sustained rate limit (5 minutes) |
| `ANALYSIS_TOP_N` | `10` | Rows printed to the console in the rampage ranking |
| `ANALYSIS_REACTION_WINDOW_SECONDS` | `60` | Reaction window after the rampage ends |
| `TOP_HEROES_COUNT` | `60` | Number of top heroes to query (legacy) |
| `TOP_PLAYERS_PER_HERO` | `3` | Top players per hero (legacy) |
| `TOP_MATCHES_PER_PLAYER` | `3` | Recent matches per top player (legacy) |
| `LEADERBOARD_BRACKET` | `IMMORTAL` | Leaderboard bracket (legacy) |
| `SPECIFIC_TOP_HEROES` | `{86:50, 74:25, ...}` | Hero-specific top player counts (legacy + harvest phase 3) |
| `SPECIFIC_TOP_MATCHES_PER_PLAYER` | `2` | Recent matches per specific-top player (legacy) |
| `HERO_STATS_BRACKETS` | `[HERALD..IMMORTAL]` | Brackets used in `heroStats` queries (legacy) |
| `DAILY_MATCH_TARGET` | `2900` | Daily harvest target of new distinct match IDs |
| `DAILY_MATCH_MAX_AGE_DAYS` | `7` | Max age of harvested matches |
| `DAILY_RAMPAGE_TAKE` | `20` | Rampages per hero in the harvest (Stratz max) |
| `PLAYERS_BATCH_SIZE` | `5` | Accounts per `players(...)` call (Stratz max) |
| `PLAYER_RECENT_MATCHES_TAKE` | `5` | Recent matches per player in the harvest |
| `PRO_PLAYERS_LIMIT` | `600` | Max pro players scanned per harvest |
| `RELEVANT_HERO_LEADERBOARD_TAKE` | `25` | Leaderboard players per unique-mechanics hero |
| `TOP_HERO_LEADERBOARD_TAKE` | `10` | Leaderboard players per most-played/winrate hero |
| `DAILY_TOP_HEROES_COUNT` | `40` | Most-played heroes scanned in the harvest |
| `DAILY_WINRATE_HEROES_COUNT` | `20` | Highest-winrate heroes scanned in the harvest |
| `WINRATE_MIN_MATCHES` | `1000` | Min weekly matches for the winrate ranking |

## Dependencies

- `python-dotenv` — loads `.env` file.
- Standard library: `os`, `pathlib`

## Inputs

- Environment variables from `.env` or shell:
  - `STRATZ_API_KEY` (required)
  - `OPENDOTA_API_KEY` (optional)
  - `GOOGLE_DRIVE_CLIENT_SECRETS` (optional) — path to the Drive OAuth client secret JSON
  - `GOOGLE_DRIVE_TOKEN_PATH` (optional) — where the OAuth token is saved
  - `GOOGLE_DRIVE_FOLDER_ID` (optional) — shared Drive folder ID

## Outputs

- Class-level constants used throughout the application.
- Validation exception if required variables are missing.

## Usage example

```python
from config import Config

Config.validate()
print(Config.BASE_URL)
print(Config.RAMPAGE_TAKE)
```

## Rules

- Any new environment variable must be added to `.env.example`.
- Prefer class-level constants over hardcoded values.
- Provide sensible defaults for non-secret values.
