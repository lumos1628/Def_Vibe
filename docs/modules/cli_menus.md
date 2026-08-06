# `cli/menus.py` — Interactive Menus

## Purpose

Contains all interactive CLI menu logic: displaying options, reading user input, and dispatching choices to the appropriate services.

Separating menus from `main.py` makes the entry point smaller and allows menu behavior to be tested in isolation.

## Public functions

### `show_main_menu() -> int | None`

Displays the main menu and returns the selected option (1-4) or `None` if invalid.

### `show_search_menu() -> int | None`

Displays the search submenu and returns the selected option (1-5) or `None`.

### `run_search_menu(service_factory: ServiceFactory) -> None`

Dispatches search submenu choices to the appropriate discovery services.

### `show_parse_menu() -> int | None`

Displays the parse submenu and returns the selected option (1-3) or `None`.

### `run_parse_menu(service_factory: ServiceFactory) -> None`

Dispatches parse submenu choices to `ParseService`.

### `show_export_menu() -> int | None`

Displays the export submenu and returns the selected option (1-3) or `None`.

### `run_export_menu(service_factory: ServiceFactory) -> None`

Dispatches export submenu choices to `ExportService`.

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
