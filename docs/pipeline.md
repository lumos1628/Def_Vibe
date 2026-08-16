# Pipeline

## Startup flow

When the application starts (`main.main()`), it performs the following steps:

1. `Config.validate()` — ensures `STRATZ_API_KEY` is set.
2. `ServiceFactory` — creates database, clients, and repositories (including `DriveService`).
3. `factory.db.init()` — creates SQLite tables if they do not exist.
4. `factory.db.migrate()` — adds missing columns and tables to existing databases.
5. `factory.hero_service().ensure_synced()` — downloads the hero list once.
6. `factory.chat_wheel_service().ensure_synced()` — loads the chat wheel catalog once.
7. Main menu loop starts.

## Main menu

```
1. Buscar y almacenar IDs
2. Parse
3. Exportar data
4. Analizar data
5. Salir
```

## Phase 1: Search and store IDs (daily harvest)

This phase discovers match IDs and stores them in `rampage_matches`.

### Submenu

```
1. Cosecha diaria
2. Volver al menú principal
```

`TopHeroesService`, `RampageService`, and `SpecificTopService` are legacy discovery services: they still exist and are wired in `ServiceFactory`, but no menu option reaches them anymore.

### Workflow for `Cosecha diaria`

`DailyHarvestService.harvest()` collects up to `Config.DAILY_MATCH_TARGET` (2900) new distinct `match_id` values, all at most `Config.DAILY_MATCH_MAX_AGE_DAYS` (7) days old, deduplicated globally against every ID already stored. The phases run in priority order and each one stops as soon as the target is reached:

1. **Phase 1 — recent rampages**: `RECENT_RAMPAGES_QUERY` per hero, all brackets, `take=20` (Stratz max). The response inlines `match.startDateTime`, so no extra date queries are needed; entries older than the cutoff are skipped client-side.
2. **Phase 2 — pro players**: `PRO_PLAYERS_QUERY` (pro accounts), then their recent matches in batches of at most `Config.PLAYERS_BATCH_SIZE` (5, Stratz max) accounts per request.
3. **Phase 3 — leaderboard of unique-mechanics heroes**: top leaderboard players of `Config.SPECIFIC_TOP_HEROES` and their recent matches on those heroes.
4. **Phase 4 — most-played heroes**: ranking from `HERO_STATS_WIN_WEEK_QUERY` (`winWeek`).
5. **Phase 5 — highest-winrate heroes**: same query, filtered by `Config.WINRATE_MIN_MATCHES` weekly matches to reduce noise.

### Data stored

- `match_id`
- `hero_id`
- `played_at` (start time of the match)
- `steam_account_id`
- `extracted_at` (when the row was inserted)

### After the harvest

The CLI automatically calls `ExportService.export_match_ids_csv()` with the IDs saved in the run:

1. Writes `exports/match_ids_YYYY-MM-DD.csv` (one `match_id` per row).
2. Uploads it to Google Drive (when configured) so the Tecsup machine can pick it up.

## Phase 2: Parse

This phase uses the OpenDota API to replay-parse matches.

### Submenu

```
1. Parsear
2. Encolar parses desde CSV (Tecsup)
3. Descargar parses desde CSV (casa)
4. Limpiar IDs antiguas
5. Volver al menú principal
```

### Workflow for `Parsear`

With `Config.PARSE_GET_ONLY` enabled (default), parsing only issues GETs — no parse jobs are enqueued and nothing is polled:

1. **Load batch** — reads up to `Config.PARSE_BATCH_SIZE` matches with `parse_status` in `pending`, `queued`, or `parsing`.
2. **Verify** — for each match, calls `GET /matches/{match_id}`.
   - If the match already has `chat` or `kills_log`, saves the JSON to `data/replays/{match_date}/{match_id}.json`, registers it in the `match_details` index, and marks it `done`.
   - Otherwise, leaves it `pending` to be retried on a later run.

When `PARSE_GET_ONLY` is disabled, the legacy flow runs instead: matches are marked `data_verified`, parses are requested via `POST /request/{match_id}`, the returned `jobId`s are polled (`PARSE_POLL_INTERVAL`, up to `PARSE_MAX_POLLS`), and completed jobs are fetched and saved. Matches older than `MAX_REPLAY_AGE_DAYS` are marked `unparseable`.

### Parse states

```
pending → queued → parsing → done
                    ↘ failed / unparseable
```

### `Limpiar IDs antiguas`

- Deletes matches (and their index rows, export logs, and replay files) older than `CLEAN_OLD_MATCHES_DAYS` (default 7 days). Filtering uses the `match_date` index — no JSON scanning.

### Workflow for `Encolar parses desde CSV (Tecsup)`

Intended to run at the institute on a machine with its own OpenDota quota/IP. No local database is touched.

1. Pick a `exports/match_ids_*.csv`. When no local CSV exists, the menu offers to download the most recent one from Google Drive.
2. For each ID, call `POST /request/{match_id}` with progress `[i/N]` and the usual 429 pause.
3. IDs that return no job (already parsed or no replay) are counted separately, not treated as errors.
4. Writes `exports/parse_jobs_YYYY-MM-DD.csv` with the `(match_id, job_id)` pairs for traceability. This file stays local.

### Workflow for `Descargar parses desde CSV (casa)`

Intended to run at home once the parses were enqueued at the institute. Saves OpenDota quota by skipping work already done.

1. Pick a `exports/match_ids_*.csv`.
2. `MatchRepository.list_downloadable()` filters out IDs already `done` with replay data and `unparseable` ones (they are reported as skipped).
3. For each remaining ID, call `GET /matches/{match_id}`.
4. If the match has replay data, save the JSON file under `data/replays/{match_date}/`, update the `match_details` index, and mark `parse_status = 'done'`.
5. If the parse is not ready yet (OpenDota queues can take hours), the match is left `pending` to be retried on a later run.
6. Once every ID in the CSV is `done` or `unparseable`, the CLI asks whether to delete the CSV locally and on Drive (`cleanup_consumed_csv()`).

## Phase 3: Export data

This phase reads parsed match data and generates reports.

### Submenu

```
1. Exportar kills y chats
2. Re-exportar partidas parseadas hoy
3. Volver al menú principal
```

### Workflow for `Exportar kills y chats`

1. Loads matches parsed today that have not been exported yet.
2. For each match:
   - Builds chat rows from `chat` array.
   - Resolves chat wheel IDs using the `chat_wheels` table.
   - Builds kill rows from `kills_log` arrays.
   - Detects the rampage window (5 kills within 18 seconds).
3. Writes `chats.csv` and `kills.csv` to `exports/YYYY-MM-DD/`.
4. Writes `rampage_export_YYYY-MM-DD.xlsx` with styled sheets.
5. Records each exported match in `export_log` to avoid re-exporting.

### `Re-exportar partidas parseadas hoy`

- Clears today's export log entries for matches parsed today.
- Re-runs the export process.

## Phase 4: Analyze data

`AnalysisService.export_top()` (main menu option `4`) builds a combined rampage ranking from the parsed replay files — no API calls.

1. Pick a played date or all dates.
2. Reads only matches with `parse_status = 'done'` and `has_replay_data = 1`.
3. For each match, detects the **shortest** 5-kill window (≤18s) among the match's heroes (`racha_seg`).
4. Counts reactions: chat messages within `Config.ANALYSIS_REACTION_WINDOW_SECONDS` (60s) after the rampage ends.
5. Scores rank-based within the selection (best speed = N points, most reactions = N points).
6. Writes `exports/rampages/rampages_YYYY-MM-DD.csv` (or `rampages_all.csv` for all dates).

## Rate limiting and resilience

- Stratz requests are spaced by `REQUEST_DELAY` (0.5s) and retried up to `MAX_RETRIES` times.
- OpenDota requests are spaced by `OPENDOTA_REQUEST_DELAY` (0.65s).
- OpenDota 429 responses are handled with `Retry-After` or exponential backoff.
- After `RATE_LIMIT_MAX_RETRIES` consecutive 429s, parsing pauses for `RATE_LIMIT_PAUSE_SECONDS` (300s = 5 minutes) and resumes from the same item.

## Google Drive flow (match IDs CSV)

The only file that crosses machines through Drive is `exports/match_ids_*.csv`:

- **Home** runs the harvest → the CSV is uploaded to the shared folder.
- **Tecsup** (own OpenDota quota/IP) downloads the CSV from Drive, enqueues parses, and keeps `parse_jobs_*.csv` local.
- **Home** downloads the parsed matches; once all IDs in the CSV are `done` or `unparseable`, the CSV is deleted locally and from Drive.

Excel/chat/kill exports, the rampage ranking, the replay JSONs, and `parse_jobs_*.csv` stay **local only**.
