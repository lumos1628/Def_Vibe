# `services/export_service.py` — ExportService

## Purpose

Reads parsed match data from the database and generates daily reports: two CSV files (`chats.csv`, `kills.csv`) and one styled Excel workbook.

## Public functions

### `class ExportService`

#### `__init__(hero_repository, match_repository, chat_wheel_repository)`

Loads the hero list and builds lookup tables for hero names and short-name-to-ID mappings.

#### `export_chat_kills(output_path, today) -> tuple[Path, Path, Path]`

Main export function. Returns paths to `chats.csv`, `kills.csv`, and the Excel file.

#### `export_chat_kills_csv(output_path) -> Path`

Convenience wrapper that returns only the Excel path.

#### `reexport_parsed_today(output_path) -> tuple[Path, Path, Path]`

Clears today's export log entries for matches parsed today and re-runs the export.

## Internal flow

1. Determine the target directory: `output_path` or `exports/YYYY-MM-DD`.
2. Load matches parsed today that are not yet in `export_log`.
3. For each match:
   - Build chat rows from the `chat` array (`_build_chat_rows`).
   - Resolve chat wheel IDs using `ChatWheelRepository.get_by_id()` (`_resolve_chat_message`).
   - Build kill rows from the `kills_log` arrays (`_build_kill_rows`).
   - Detect the rampage window (`_detect_rampage`): 5 kills within 18 seconds.
4. Write CSV files with `csv.DictWriter`.
5. Write the Excel workbook with styled sheets (`_write_excel`, `_style_sheet`).
6. Mark each exported match in `export_log`.

## Dependencies

- `openpyxl` — Excel generation.
- `csv` — CSV generation.
- `repositories.hero_repository.HeroRepository`
- `repositories.match_repository.MatchRepository`
- `repositories.chat_wheel_repository.ChatWheelRepository`
- `config.Config`

## Inputs

- Parsed match data from `match_details`.
- Hero catalog and chat wheel catalog from the database.
- Optional `output_path` and `today` override.

## Outputs

- `exports/YYYY-MM-DD/chats.csv`
- `exports/YYYY-MM-DD/kills.csv`
- `exports/YYYY-MM-DD/rampage_export_YYYY-MM-DD.xlsx`
- Records in `export_log`.

## Usage example

```python
from database import Database
from repositories.chat_wheel_repository import ChatWheelRepository
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository
from services.export_service import ExportService

db = Database()
hero_repo = HeroRepository(db)
match_repo = MatchRepository(db)
chat_wheel_repo = ChatWheelRepository(db)

service = ExportService(hero_repo, match_repo, chat_wheel_repo)
chats_csv, kills_csv, xlsx = service.export_chat_kills()
print(f"Exported to {xlsx}")
```

## Field lists

- `CHAT_FIELDNAMES` and `KILL_FIELDNAMES` define the CSV/Excel column order.
- See `docs/csv_format.md` for column descriptions.
