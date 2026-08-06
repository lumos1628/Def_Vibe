# `services/parse_service.py` — ParseService

## Purpose

Processes a batch of discovered matches through the OpenDota API. It verifies match data, requests replay parses when needed, polls job statuses, and stores the full JSON responses.

## Public functions

### `class ParseService`

#### `__init__(client, match_repository)`

Stores the OpenDota client and match repository.

#### `parse_unparsed() -> tuple[int, int, int, int, int]`

Main parse loop.

Returns a tuple of:

- matches with replay data
- matches queued
- matches still queued/processing
- matches that failed to enqueue
- total matches processed

#### `clean_old_matches(days: int | None = None) -> None`

Deletes matches (and their details/export logs) older than `Config.CLEAN_OLD_MATCHES_DAYS` (default 7 days).

## Internal flow

`parse_unparsed()` runs in phases:

1. **Load batch**
   - `MatchRepository.list_unparsed(Config.PARSE_BATCH_SIZE)` returns match IDs.

2. **Verify / enqueue** (`_enqueue_unparsed`)
   - For each match, call `OpenDotaClient.get_match()`.
   - Save JSON to `match_details` via `MatchRepository.save_match_details()`.
   - Mark the match as `data_verified`.
   - If the match already has chat/kill data, mark as `done`.
   - If the match is older than `MAX_REPLAY_AGE_DAYS`, mark as `unparseable`.
   - Otherwise, request a parse via `OpenDotaClient.request_parse()` and store the `jobId`.

3. **Poll jobs** (`_poll_jobs`)
   - For each queued job, wait `PARSE_POLL_INTERVAL` seconds.
   - Call `OpenDotaClient.get_request_status()`.
   - When completed, fetch the match again and save it.
   - Repeat up to `PARSE_MAX_POLLS` times.

4. **Retry direct fetch** (`_fetch_done_matches`)
   - If jobs are still pending after polling, try fetching the match directly.

5. **Rate-limit handling**
   - On `RateLimitError`, pause for `RATE_LIMIT_PAUSE_SECONDS` and resume from the same item.

## Dependencies

- `api.opendota_client.OpenDotaClient`, `RateLimitError`
- `repositories.match_repository.MatchRepository`
- `config.Config`

## Inputs

- Match IDs from `rampage_matches` with `parse_status` in `pending`, `queued`, or `parsing`.
- OpenDota API responses.
- Environment: optional `OPENDOTA_API_KEY`.

## Outputs

- JSON stored in `match_details`.
- `parse_status`, `has_replay_data`, `unparseable`, and related fields updated in `rampage_matches`.
- Console progress messages.

## Usage example

```python
from api.opendota_client import OpenDotaClient
from database import Database
from repositories.match_repository import MatchRepository
from services.parse_service import ParseService

db = Database()
client = OpenDotaClient()
repo = MatchRepository(db)

service = ParseService(client, repo)
done, queued, still, failed, total = service.parse_unparsed()
print(f"Done: {done}, Queued: {queued}, Still: {still}, Failed: {failed}, Total: {total}")

service.clean_old_matches()
```
