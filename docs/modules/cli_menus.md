# `cli/menus.py` — Interactive Menus

## Purpose

Contains all interactive CLI menu logic: displaying options, reading user input, and dispatching choices to the appropriate services.

Separating menus from `main.py` makes the entry point smaller and allows menu behavior to be tested in isolation.

## Public functions

### `show_main_menu() -> int | None`

Displays the main menu and returns the selected option (1-5) or `None` if invalid. Option `4` opens the analysis submenu (`run_analysis_menu`).

### `show_search_menu() -> int | None`

Displays the search submenu and returns the selected option (1-3) or `None`.

### `run_search_menu(service_factory: ServiceFactory) -> None`

Dispatches search submenu choices. Option 1 runs the daily harvest (`DailyHarvestService.harvest()`), which exports the saved IDs to a `match_ids_*.csv` (and uploads it to Drive) when any were saved. Option 2 re-uploads the most recent local `exports/match_ids_*.csv` to Google Drive (`DriveService.upload`) without running a new harvest.

### `show_parse_menu() -> int | None`

Displays the parse submenu and returns the selected option (1-5) or `None`.

### `run_parse_menu(service_factory: ServiceFactory) -> None`

Dispatches parse submenu choices to `ParseService`. Options 2 and 3 use `_pick_match_ids_csv()` to let the user choose a `match_ids_*.csv` before calling `enqueue_from_csv()`/`download_from_csv()`. After a successful `download_from_csv()` run, if every ID in the CSV is `done` or `unparseable`, the CLI asks whether to delete the CSV locally and on Drive (`cleanup_consumed_csv()`).

### `_pick_match_ids_csv(parse_service) -> Path | None`

Lists the available `exports/match_ids_*.csv` via `ParseService.list_match_ids_csvs()`, lets the user pick one, and returns the path (or `None` on invalid input or no files). When no local file exists and Drive is configured, it offers to download the most recent `match_ids_*.csv` from Google Drive (`download_latest_match_ids_from_drive()`).

### `show_export_menu() -> int | None`

Displays the export submenu and returns the selected option (1-3) or `None`.

### `run_export_menu(service_factory: ServiceFactory) -> None`

Dispatches export submenu choices to `ExportService`.

### `show_analysis_menu() -> int | None`

Displays the analysis submenu and returns the selected option or `None`.

### `run_analysis_menu(service_factory: ServiceFactory) -> None`

Dispatches analysis submenu choices to `AnalysisService.export_top()` (a specific date or all dates).

## Dependencies

- `cli.factory.ServiceFactory`

## Inputs

- User input via `input()`.
- `ServiceFactory` for dispatching actions.

## Outputs

- Console output.
- Service calls that may modify the database or generate files.

## Usage example

```python
from cli.factory import ServiceFactory
from cli.menus import show_main_menu, run_search_menu

factory = ServiceFactory()
choice = show_main_menu()
if choice == 1:
    run_search_menu(factory)
```
