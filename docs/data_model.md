# Data Model

## Database

The application uses a single SQLite database file (`data.db`).

## Tables created by `Database.init()`

### `heroes`

Catalog of Dota 2 heroes.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `INTEGER PRIMARY KEY` | Hero ID |
| `display_name` | `TEXT NOT NULL` | Human-readable name |
| `short_name` | `TEXT NOT NULL` | Short/internal name |
| `synced_at` | `TEXT NOT NULL` | ISO timestamp of sync |

### `rampage_matches`

Core table for discovered matches.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Internal row ID |
| `match_id` | `INTEGER NOT NULL` | Dota 2 match ID |
| `hero_id` | `INTEGER NOT NULL` | Hero involved in the match |
| `played_at` | `TEXT NOT NULL` | Match start timestamp |
| `steam_account_id` | `INTEGER NOT NULL` | Player account ID |
| `extracted_at` | `TEXT NOT NULL` | When the match was discovered |
| `parsed` | `INTEGER NOT NULL DEFAULT 0` | Legacy parse flag |
| `has_replay_data` | `INTEGER NOT NULL DEFAULT 0` | Whether parsed data contains kills/chat |
| `data_verified` | `INTEGER NOT NULL DEFAULT 0` | Whether the match has been verified via OpenDota |
| `parse_requested_at` | `TEXT` | When parse was requested |
| `parse_request_count` | `INTEGER NOT NULL DEFAULT 0` | How many times parse was requested |
| `parse_job_id` | `TEXT` | OpenDota job ID |
| `parse_status` | `TEXT DEFAULT 'pending'` | `pending`, `queued`, `parsing`, `done`, `failed` |
| `last_parse_attempt_at` | `TEXT` | Last parse attempt timestamp |
| `unparseable` | `INTEGER NOT NULL DEFAULT 0` | Whether the match cannot be parsed |

**Constraints**
- `FOREIGN KEY (hero_id) REFERENCES heroes(id)`
- `UNIQUE (hero_id, match_id)`

**Indexes**
- `idx_rampage_hero` on `hero_id`
- `idx_rampage_parse_status` on `parse_status`
- `idx_rampage_last_attempt` on `last_parse_attempt_at`
- `idx_rampage_parsed` on `parsed`

### `export_log`

Tracks which matches have been exported.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Internal row ID |
| `match_id` | `INTEGER NOT NULL` | Exported match ID |
| `exported_at` | `TEXT NOT NULL` | Export timestamp |
| `output_path` | `TEXT NOT NULL` | Directory where output was saved |

**Constraint**
- `UNIQUE(match_id)`

**Index**
- `idx_export_match` on `match_id`

### `chat_wheels`

Catalog of chat wheel messages.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `INTEGER PRIMARY KEY` | Chat wheel ID |
| `name` | `TEXT NOT NULL` | Internal name |
| `label` | `TEXT NOT NULL` | Display label |
| `message` | `TEXT NOT NULL` | Actual message text |
| `all_chat` | `INTEGER DEFAULT 0` | Whether it is sent to all chat |
| `synced_at` | `TEXT NOT NULL` | Sync timestamp |

## Tables created by `Database.migrate()`

### `match_details`

Stores the raw JSON response from OpenDota for each parsed match.

| Column | Type | Notes |
|--------|------|-------|
| `match_id` | `INTEGER PRIMARY KEY` | Dota 2 match ID |
| `opendota_data` | `TEXT NOT NULL` | Full JSON string |
| `parsed_at` | `TEXT NOT NULL` | When the data was saved |

## Migrations

`Database.migrate()` is responsible for:

- Adding missing columns to `rampage_matches` (`parsed`, `has_replay_data`, `data_verified`, `parse_requested_at`, `parse_request_count`, `parse_job_id`, `parse_status`, `last_parse_attempt_at`, `unparseable`).
- Creating the `match_details` table.
- Creating missing indexes.
- Backfilling `has_replay_data` from existing `match_details` JSON.
- Backfilling `parse_status` based on existing flags.
- Backfilling `data_verified` based on existing parse state.
- Resetting `unparseable` for recent matches so they can be retried.
- Adding `short_name` to `heroes` if missing (and clearing the table to re-sync).

This allows the application to evolve its schema without losing data.
