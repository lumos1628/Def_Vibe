# CSV/Excel Format

## Output directory

Exports are written to:

```
exports/YYYY-MM-DD/
```

Each directory contains:

- `chats.csv`
- `kills.csv`
- `rampage_export_YYYY-MM-DD.xlsx`

## `match_ids_YYYY-MM-DD.csv`

Written after every daily harvest and uploaded to Google Drive (when configured). Meant to be shared so the IDs can be parsed by a third party (e.g., another OpenDota API key / IP).

| Column | Description |
|--------|-------------|
| `match_id` | Dota 2 match ID |

One `match_id` per row; the order is the sorted list of IDs saved during the harvest run.

## `parse_jobs_YYYY-MM-DD.csv`

Written by `parse_service.enqueue_from_csv()` (menu `2` → option `2`, run at the institute). Traceability of the enqueued OpenDota parse jobs. Stays **local only** — it is never uploaded to Drive.

| Column | Description |
|--------|-------------|
| `match_id` | Dota 2 match ID |
| `job_id` | OpenDota parse job ID returned by `POST /request/{match_id}` |

## `chats.csv`

| Column | Description |
|--------|-------------|
| `match_id` | Dota 2 match ID |
| `chat_time` | Message time in seconds from match start |
| `chat_time_min` | Message time in minutes |
| `chat_message` | Resolved text of the message or chat wheel |
| `chat_type` | Message type (e.g., `chatwheel`, `chat`) |
| `chat_is_chatwheel` | `1` if the message is a chat wheel, `0` otherwise |
| `chat_wheel_id` | Chat wheel ID if applicable |
| `sender_hero_id` | Hero ID of the sender |
| `sender_hero_name` | Display name of the sender's hero |
| `sender_slot` | Sender slot value |
| `sender_player_slot` | Dota 2 `player_slot` of the sender |
| `has_replay_data` | `1` if the match has replay data, `0` otherwise |
| `unparseable` | `1` if the match was marked unparseable, `0` otherwise |

## `kills.csv`

| Column | Description |
|--------|-------------|
| `match_id` | Dota 2 match ID |
| `kill_time` | Kill time in seconds from match start |
| `kill_time_min` | Kill time in minutes |
| `killer_hero_id` | Hero ID of the killer |
| `killer_hero_name` | Display name of the killer's hero |
| `victim_hero_id` | Hero ID of the victim |
| `victim_hero_name` | Display name of the victim's hero |
| `rampage_time` | Start time of the detected rampage window (seconds) |
| `rampage_time_min` | Rampage start time in minutes |
| `is_rampage_kill` | `1` if this kill is part of the rampage, `0` otherwise |
| `has_replay_data` | `1` if the match has replay data, `0` otherwise |
| `unparseable` | `1` if the match was marked unparseable, `0` otherwise |

## Excel workbook

**File:** `rampage_export_YYYY-MM-DD.xlsx`

**Sheets:**
- `Chats` — same data as `chats.csv`
- `Kills` — same data as `kills.csv`

**Styling:**
- Header row: dark gray background (`#334155`) with white bold text.
- Data rows: alternating light green shades (`#D1FAE5` and `#A7F3D0`) grouped by `match_id`.
- Font: dark gray text, size 10.
- Auto-filter enabled.
- Frozen top row.
- Column widths are auto-adjusted based on content.

## Rampage detection

A rampage is detected when a player has **5 consecutive kills** within **18 seconds** in the `kills_log` of the hero associated with the match.

The `is_rampage_kill` flag is set to `1` for all 5 kills that form the first such window.

## Rampage analysis ranking

Written by the analysis submenu (main menu option `4`) to `exports/rampages/`:

- `rampages_YYYY-MM-DD.csv` — one ranking per selected played date.
- `rampages_all.csv` — ranking across all dates.

**File:** `rampages_<selection>.csv`

| Column | Description |
|--------|-------------|
| `rank` | Position in the combined ranking |
| `match_id` | Dota 2 match ID |
| `fecha_partida` | Match start date (`played_at`) |
| `hero_id` | Hero that achieved the rampage |
| `hero_name` | Display name of that hero |
| `rampage_time` | In-game start of the rampage window (seconds) |
| `rampage_time_min` | Rampage start in minutes |
| `racha_seg` | Duration of the shortest 5-kill window (≤18s) |
| `n_reacciones` | Chat messages within `Config.ANALYSIS_REACTION_WINDOW_SECONDS` (60s) after the rampage ends |
| `puntaje_racha` | Rank-based points for speed (shortest racha = N) |
| `puntaje_reacciones` | Rank-based points for reactions (most reactions = N) |
| `puntaje_total` | `puntaje_racha + puntaje_reacciones` |
| `chats_reaccion` | Reaction chats joined as `[mm:ss] Héroe: mensaje`, separated by `\|` |

**Notes**
- Only matches with `parse_status = 'done'` and `has_replay_data = 1` are considered.
- Matches without a detectable rampage are excluded from the ranking.
- Reactions are measured from the moment the rampage completes (the 5th kill).
- The top `Config.ANALYSIS_TOP_N` rows are also printed to the console.

## Chat wheel resolution

During export, chat wheel IDs are translated using the `chat_wheels` table:

- The `label` field is preferred.
- If `label` is missing, `message` is used.
- If both are missing, the `name` field is used.
- If the chat wheel ID is not found, the output is `chatwheel:{id}`.

## Notes

- Matches without chats or kills are omitted from the CSV/Excel files.
- Every processed match is still recorded in the `export_log` table so it is not re-exported on later runs.
