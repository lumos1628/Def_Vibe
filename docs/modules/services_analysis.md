# `services/analysis_service.py` — AnalysisService

## Purpose

Builds a combined rampage ranking from the parsed replay files — **no API calls**. It is used by the analysis submenu (main menu option `4`). Scoring is rank-based within the selected group: the rampage with the shortest 5-kill window and the one with the most in-game chat reactions score more points.

## Public functions

### `class AnalysisService`

#### `__init__(hero_repository, match_repository, chat_wheel_repository)`

Stores the repositories and builds the hero-name lookup table.

#### `list_dates() -> list[tuple[str, int]]`

Returns the parsed dates (`played_at` prefix) with distinct match counts, newest first. Used to present the date selection.

#### `export_top(date_prefix: str | None = None) -> Path | None`

Builds the combined ranking for a date (or all dates when `None`) and exports it as CSV:

1. `MatchRepository.list_parsed_rows_by_date()` returns `(match_id, played_at, hero_id)` rows for matches with `parse_status = 'done'` and `has_replay_data = 1`.
2. `_build_records()` groups by match and detects the shortest rampage per match.
3. `_rank_records()` computes the rank-based scores.
4. `_print_top()` prints the top `Config.ANALYSIS_TOP_N` rows.
5. `_write_csv()` writes `exports/rampages/rampages_{date}.csv` (or `rampages_all.csv` for all dates).

Returns the CSV path, or `None` when there is no parsed data or no detectable rampage in the selection.

## Internal flow

- `_build_records(rows)` — groups rows by `match_id`, loads each match JSON via `MatchRepository.get_match_details()`, and keeps only matches with a detectable rampage.
- `_detect_shortest_rampage(hero_ids, data)` — for each hero of the match, sorts its `kills_log` and scans 5-kill windows; returns `(hero_id, start_time, end_time, duration)` of the **shortest** window with `duration <= 18s`.
- `_collect_reactions(data, rampage_end)` — chat messages within `Config.ANALYSIS_REACTION_WINDOW_SECONDS` (60s) after the rampage ends, with their sender hero name.
- `_resolve_chat_message(msg)` — resolves chat wheel IDs via `ChatWheelRepository.get_by_id()`.
- `_rank_records(records)` — `puntaje_racha` = N points for the fastest, `puntaje_reacciones` = N points for the most reactions, `puntaje_total = puntaje_racha + puntaje_reacciones`.
- `_print_top(ranked)`, `_write_csv(label, records)` — console output and CSV writing.

## Dependencies

- `repositories.hero_repository.HeroRepository`
- `repositories.match_repository.MatchRepository`
- `repositories.chat_wheel_repository.ChatWheelRepository`
- `config.Config` — `ANALYSIS_EXPORT_DIR`, `ANALYSIS_TOP_N`, `ANALYSIS_REACTION_WINDOW_SECONDS`.

## Inputs

- Parsed match data from the per-match replay files.
- Hero and chat wheel catalogs from the database.

## Outputs

- `exports/rampages/rampages_YYYY-MM-DD.csv` or `exports/rampages/rampages_all.csv`.
- Console output with the top `Config.ANALYSIS_TOP_N` rows.

## Usage example

```python
from database import Database
from repositories.chat_wheel_repository import ChatWheelRepository
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository
from services.analysis_service import AnalysisService

db = Database()
service = AnalysisService(HeroRepository(db), MatchRepository(db), ChatWheelRepository(db))
for date, count in service.list_dates():
    print(date, count)
service.export_top(date_prefix="2026-08-16")
```

## Notes

- Matches without a detectable rampage are excluded from the ranking.
- Reactions are measured from the moment the rampage completes (the 5th kill).
