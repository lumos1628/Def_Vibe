# Pipeline

## Startup flow

When the application starts (`main.main()`), it performs the following steps:

1. `Config.validate()` — ensures `STRATZ_API_KEY` is set.
2. `ServiceFactory` — creates database, clients, and repositories.
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
4. Salir
```

## Phase 1: Search and store IDs

This phase discovers match IDs and stores them in `rampage_matches`.

### Submenu

```
1. Buscar top 60 héroes + jugadores + partidas
2. Buscar por rampage divine_inmortal
3. Buscar últimos 5 rampages por héroe
4. Buscar específica top
5. Volver al menú principal
```

### Workflows

| Option | Service | What it does |
|--------|---------|--------------|
| 1 | `TopHeroesService` | Fetches the top 60 most-played heroes, then for each hero fetches the top 3 players and their 3 most recent matches. |
| 2 | `RampageService` | Fetches `RAMPAGE_TAKE` rampage matches per hero in the `DIVINE_IMMORTAL` bracket. |
| 3 | `RampageService` | Fetches the latest 5 rampage matches per hero, regardless of bracket. |
| 4 | `SpecificTopService` | Fetches top players for a configured list of heroes (e.g., Rubick, Invoker, Morphling) with configurable counts. |

### Data stored

- `match_id`
- `hero_id`
- `played_at` (start time of the match)
- `steam_account_id`
- `extracted_at` (when the row was inserted)

## Phase 2: Parse

This phase uses the OpenDota API to replay-parse matches.

### Submenu

```
1. Parsear
2. Limpiar IDs antiguas
3. Salir
```

### Workflow for `Parsear`

1. **Load batch**
   - Reads up to `Config.PARSE_BATCH_SIZE` matches with `parse_status` in `pending`, `queued`, or `parsing`.

2. **Verify / enqueue**
   - For each match, calls `GET /matches/{match_id}`.
   - Saves JSON to `match_details`.
   - If the match already has `chat` or `kills_log`, marks it as `done`.
   - If the match is older than `MAX_REPLAY_AGE_DAYS`, marks it as `unparseable`.
   - Otherwise, requests a replay parse via `POST /request/{match_id}` and stores the `jobId`.

3. **Poll jobs**
   - For each queued job, waits `PARSE_POLL_INTERVAL` seconds.
   - Calls `GET /request/{jobId}` up to `PARSE_MAX_POLLS` times.
   - When the job is completed, fetches the match again and saves it.

4. **Retry direct fetch**
   - If jobs are still queued after polling, attempts to fetch the match data directly.

### Parse states

```
pending → queued → parsing → done
                    ↘ failed / unparseable
```

### `Limpiar IDs antiguas`

- Deletes matches (and their details/export logs) older than `CLEAN_OLD_MATCHES_DAYS` (default 7 days).

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

## Rate limiting and resilience

- Stratz requests are spaced by `REQUEST_DELAY` (0.5s) and retried up to `MAX_RETRIES` times.
- OpenDota requests are spaced by `OPENDOTA_REQUEST_DELAY` (1s).
- OpenDota 429 responses are handled with `Retry-After` or exponential backoff.
- After `RATE_LIMIT_MAX_RETRIES` consecutive 429s, parsing pauses for 5 minutes and resumes.
