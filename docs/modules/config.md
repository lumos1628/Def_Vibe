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
| `EXPORT_DIR` | `Path("exports")` | Export output directory |
| `BRACKET` | `DIVINE_IMMORTAL` | Default ranked bracket |
| `REQUEST_DELAY` | `0.5` | Delay between Stratz requests |
| `OPENDOTA_REQUEST_DELAY` | `1.0` | Delay between OpenDota requests |
| `MAX_RETRIES` | `3` | Retry attempts for Stratz requests |
| `RAMPAGE_TAKE` | `2` | Rampage matches per hero per run |
| `MAX_REPLAY_AGE_DAYS` | `8` | Max replay age before marking unparseable |
| `CLEAN_OLD_MATCHES_DAYS` | `7` | Default cleanup window |
| `PARSE_BATCH_SIZE` | `1000` | Matches parsed per batch |
| `PARSE_POLL_INTERVAL` | `300` | Seconds between parse polls |
| `PARSE_MAX_POLLS` | `4` | Max poll rounds |
| `RATE_LIMIT_PAUSE_SECONDS` | `300` | Pause on sustained rate limit |
| `TOP_HEROES_COUNT` | `60` | Number of top heroes to query |
| `TOP_PLAYERS_PER_HERO` | `3` | Top players per hero |
| `TOP_MATCHES_PER_PLAYER` | `3` | Recent matches per top player |
| `SPECIFIC_TOP_HEROES` | `{86:50, 74:25, ...}` | Hero-specific top player counts |

## Dependencies

- `python-dotenv` — loads `.env` file.
- Standard library: `os`, `pathlib`

## Inputs

- Environment variables from `.env` or shell:
  - `STRATZ_API_KEY` (required)
  - `OPENDOTA_API_KEY` (optional)

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
