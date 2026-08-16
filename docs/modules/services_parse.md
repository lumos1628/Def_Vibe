# `services/parse_service.py` — ParseService

## Purpose

Processes a batch of discovered matches through the OpenDota API. It verifies match data, requests replay parses when needed, polls job statuses, and stores the full JSON responses.

## Public functions

### `class ParseService`

#### `__init__(client, match_repository, drive_service=None)`

Stores the OpenDota client, match repository, and an optional `DriveService` used by the Drive download/cleanup helpers.

#### `parse_unparsed() -> tuple[int, int, int, int, int]`

Main parse loop.

With `Config.PARSE_GET_ONLY` enabled (default) it returns `(done, not_ready, failed, len(match_ids), 0)`. Otherwise it returns a tuple of:

- matches with replay data
- matches queued
- matches still queued/processing
- matches that failed to enqueue
- total matches processed

#### `clean_old_matches(days: int | None = None) -> None`

Deletes matches (and their details/export logs) older than `Config.CLEAN_OLD_MATCHES_DAYS` (default 7 days).

#### `list_match_ids_csvs() -> list[Path]`

Returns the available `exports/match_ids_*.csv` files, newest first.

#### `download_latest_match_ids_from_drive() -> Path | None`

Downloads the most recent `match_ids_*.csv` from the shared Drive folder to `exports/` and returns its local path, or `None` on failure (Drive disabled, no remote files, or download error).

#### `count_pending_for_csv(csv_path) -> int`

Returns how many IDs in a `match_ids_*.csv` are still `pending`/`queued`/`parsing` in the local database (via `MatchRepository.count_pending_status()`).

#### `cleanup_consumed_csv(csv_path) -> None`

Deletes a fully processed `match_ids_*.csv` locally and on Drive. Only runs when every ID in the CSV is already `done` or `unparseable`, so pending matches are never lost.

#### `enqueue_from_csv(csv_path: Path) -> tuple[int, int, int]`

Enqueues replay parses for every ID in a `match_ids_*.csv`. Intended to run on a machine with its own OpenDota quota/IP (e.g. at the institute). Does not touch the local database.

- For each ID, calls `OpenDotaClient.request_parse()` with progress `[i/N]` and 429 pause handling.
- IDs with no job (already parsed or no replay) are counted as `no_job`, not errors.
- Writes `exports/parse_jobs_YYYY-MM-DD.csv` with the `(match_id, job_id)` pairs.
- Returns `(enqueued, no_job, failed)`.

#### `download_from_csv(csv_path: Path) -> tuple[int, int, int, int]`

Downloads parsed matches listed in a `match_ids_*.csv`. Intended to run at home after parses were enqueued elsewhere.

- Filters IDs through `MatchRepository.list_downloadable()` to skip already-done and `unparseable` matches (saves quota).
- For each remaining ID, calls `OpenDotaClient.get_match()`.
- Matches with replay data are saved via `save_match_details()` (JSON file + index + `done`).
- Matches whose parse is not ready yet are left `pending` for a later run.
- Returns `(downloaded, not_ready, skipped, failed)`.

## Internal flow

`parse_unparsed()` loads the batch with `MatchRepository.list_unparsed(Config.PARSE_BATCH_SIZE)` and then runs in one of two modes:

**GET-only mode** (`Config.PARSE_GET_ONLY = True`, default):

1. For each match, call `OpenDotaClient.get_match()`.
2. If the data already has `chat`/`kills_log`, save the JSON via `MatchRepository.save_match_details()` (file + index) and mark it `done`.
3. Otherwise, leave the match `pending` to be retried on a later run. No parse jobs are enqueued and nothing is polled.

**Legacy mode** (`PARSE_GET_ONLY` disabled):

1. **Verify / enqueue** (`_enqueue_unparsed`)
   - For each match, call `OpenDotaClient.get_match()`.
   - Save JSON to a per-match file via `MatchRepository.save_match_details()` (registered in the `match_details` index).
   - Mark the match as `data_verified`.
   - If the match already has chat/kill data, mark as `done`.
   - If the match is older than `MAX_REPLAY_AGE_DAYS`, mark as `unparseable`.
   - Otherwise, request a parse via `OpenDotaClient.request_parse()` and store the `jobId`.

2. **Poll jobs** (`_poll_jobs`)
   - For each queued job, wait `PARSE_POLL_INTERVAL` seconds.
   - Call `OpenDotaClient.get_request_status()`.
   - When completed, fetch the match again and save it.
   - Repeat up to `PARSE_MAX_POLLS` times.

3. **Retry direct fetch** (`_fetch_done_matches`)
   - If jobs are still pending after polling, try fetching the match directly.

4. **Rate-limit handling**
   - On `RateLimitError`, pause for `RATE_LIMIT_PAUSE_SECONDS` and resume from the same item.

## Dependencies

- `api.opendota_client.OpenDotaClient`, `RateLimitError`
- `repositories.match_repository.MatchRepository`
- `services.drive_service.DriveService` (optional)
- `config.Config`

## Inputs

- Match IDs from `rampage_matches` with `parse_status` in `pending`, `queued`, or `parsing`.
- OpenDota API responses.
- Environment: optional `OPENDOTA_API_KEY`.

## Outputs

- JSON stored in per-match files under `data/replays/` (indexed by `match_details`).
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
