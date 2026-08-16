# `api/opendota_client.py` — OpenDotaClient

## Purpose

Wraps the OpenDota REST API. It is used to fetch match details, request replay parses, and poll parse job status. It includes robust handling of HTTP 429 (rate limit) responses with exponential backoff.

## Public functions

### `class OpenDotaClient`

#### `__init__()`

Creates a `requests.Session`, sets the base URL, and initializes the rate-limit counter.

#### `reset_rate_limit_count() -> None`

Resets the internal consecutive-429 counter.

#### `get_match(match_id: int) -> dict[str, Any] | None`

Fetches a match by ID.

- Returns `None` if the match is not found (HTTP 404).
- Returns the parsed JSON response otherwise.
- Raises on other HTTP errors.

#### `request_parse(match_id: int) -> str | None`

Requests a replay parse for a match.

- Returns the OpenDota `jobId` if the request succeeds.
- Returns `None` on 404/400 or if the job ID is missing.
- Raises on other HTTP errors.

#### `get_request_status(job_id: str) -> dict[str, Any] | None`

Polls the status of a parse job.

- Returns `None` on 404.
- Returns the parsed JSON otherwise.

#### `pause() -> None`

Sleeps for `Config.OPENDOTA_REQUEST_DELAY` (0.65s by default). Called automatically after every request.

### `class RateLimitError(Exception)`

Raised when the client receives `Config.RATE_LIMIT_MAX_RETRIES` consecutive HTTP 429 responses.

## Internal flow

1. `_build_url(path)` appends the optional `api_key` query parameter if `OPENDOTA_API_KEY` is set.
2. `_request(method, path, ...)` sends the request.
3. If the response is `429`, increment the counter, wait `Retry-After` or exponential backoff, and retry. If the counter reaches the limit, raise `RateLimitError`.
4. If the response is not `429`, reset the counter and return the response.
5. On network errors, retry up to `Config.PARSE_MAX_RETRIES`.
6. `pause()` is executed in a `finally` block after every request.

## Dependencies

- `requests` — HTTP client.
- `config.Config` — base URL, API key, delays, retry limits.

## Inputs

- `match_id` (int): Dota 2 match ID.
- `job_id` (str): OpenDota parse job ID.
- Environment: optional `OPENDOTA_API_KEY` loaded via `Config`.

## Outputs

- `dict[str, Any] | None` for match and status calls.
- `str | None` for parse request calls (the job ID).
- `RateLimitError` or `requests.RequestException` on severe failures.
- Console messages (Spanish) on rate limit and retry events.

## Usage example

```python
from api.opendota_client import OpenDotaClient

client = OpenDotaClient()

# Fetch match details
match = client.get_match(123456789)
if match is None:
    print("Match not found")

# Request a replay parse
job_id = client.request_parse(123456789)
if job_id:
    status = client.get_request_status(job_id)
    print(status)
```
