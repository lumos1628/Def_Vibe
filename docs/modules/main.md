# `main.py` — Entry Point

## Purpose

The only entry point of the application. It validates configuration, initializes the database, syncs catalogs, and starts the interactive menu loop. The actual menu logic and dependency injection live in `cli/`.

## Public functions

### `main() -> None`

Application bootstrap:

1. `Config.validate()`
2. Create `ServiceFactory`
3. `Database.init()`
4. `Database.migrate()`
5. `HeroService.ensure_synced()`
6. `ChatWheelService.ensure_synced()`
7. Main menu loop via `cli.menus`

## Dependencies

- `cli.factory.ServiceFactory`
- `cli.menus` for menu display and dispatch
- `config.Config`

## Inputs

- User input via `input()` (handled by `cli.menus`).
- Environment variables via `Config`.
- Existing SQLite database.

## Outputs

- Console menu output.
- Database changes through services.
- Exported files through `ExportService`.

## Usage example

```bash
source venv/bin/activate
python main.py
```

## Rules

- `main.py` must remain the only entry point.
- All new user-facing features should be added as menu options in `cli/menus.py`.
- New services must be wired through `cli/factory.py`.
