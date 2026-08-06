# `api/client.py` — StratzClient

## Purpose

Provides a GraphQL client for the Stratz API. It handles authentication, Cloudflare bypass, retries, and basic error handling so callers can execute GraphQL queries without worrying about transport details.

## Public functions

### `class StratzClient`

#### `__init__()`

Initializes the client with the Stratz URL, authorization headers, and a `cloudscraper` instance.

#### `execute(query: str, variables: dict | None = None) -> dict[str, Any]`

Sends a GraphQL request to Stratz.

- Builds a JSON payload with `query` and optional `variables`.
- Retries up to `Config.MAX_RETRIES` on request or GraphQL errors.
- Waits `attempt * 2` seconds between retries.
- Returns the `data` field of the JSON response.
- Raises `StratzApiError` if the response contains GraphQL errors.
- Raises the last captured exception if all retries are exhausted.

#### `pause() -> None`

Sleeps for `Config.REQUEST_DELAY` (0.5 seconds by default). Should be called after each request to avoid hitting rate limits.

### `class StratzApiError(Exception)`

Raised when the Stratz API returns GraphQL errors. Stores the raw error list in `self.errors`.

## Internal flow

1. Build payload: `{"query": query, "variables": variables}`.
2. Loop for `MAX_RETRIES` attempts.
3. POST the payload using `cloudscraper` with the configured headers and a 30-second timeout.
4. Call `raise_for_status()` to catch HTTP errors.
5. Parse JSON. If `errors` key exists, raise `StratzApiError`.
6. Return `data`.
7. On failure, wait and retry. If the last attempt fails, re-raise the exception.

## Dependencies

- `cloudscraper` — Cloudflare bypass.
- `requests` — HTTP handling.
- `config.Config` — URL, API key, retry, and delay settings.

## Inputs

- `query` (str): GraphQL query string. Preferably imported from `api/queries.py`.
- `variables` (dict | None): GraphQL variables for parameterized queries.
- Environment: `STRATZ_API_KEY` loaded via `Config`.

## Outputs

- `dict[str, Any]`: The `data` object of the GraphQL response.
- Exceptions on failure: `StratzApiError`, `requests.RequestException`.
- Console progress messages (Spanish) on retry.

## Usage example

```python
from api.client import StratzClient
from api.queries import HEROES_QUERY

client = StratzClient()
result = client.execute(HEROES_QUERY)
heroes = result["constants"]["heroes"]
client.pause()
```

```python
from api.client import StratzClient
from api.queries import RAMPAGES_QUERY

client = StratzClient()
result = client.execute(
    RAMPAGES_QUERY,
    {"heroId": 86, "bracketBasicIds": ["DIVINE_IMMORTAL"], "take": 2}
)
client.pause()
```
