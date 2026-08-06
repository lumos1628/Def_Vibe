# `cli/factory.py` — ServiceFactory

## Purpose

Dependency injection container for the application. It creates and wires together all services, repositories, clients, and the database.

Separating this from `main.py` keeps the entry point minimal and makes the wiring reusable from tests or scripts.

## Public functions

### `class ServiceFactory`

#### `__init__()`

Initializes the database, Stratz client, OpenDota client, and repositories.

#### `hero_service() -> HeroService`

Creates a `HeroService` wired to the Stratz client and hero repository.

#### `chat_wheel_service() -> ChatWheelService`

Creates a `ChatWheelService` wired to the chat wheel repository.

#### `rampage_service() -> RampageService`

Creates a `RampageService` wired to the Stratz client, hero repository, and match repository.

#### `top_heroes_service() -> TopHeroesService`

Creates a `TopHeroesService` wired to the Stratz client, hero repository, and match repository.

#### `specific_top_service() -> SpecificTopService`

Creates a `SpecificTopService` wired to the Stratz client, hero repository, and match repository.

#### `parse_service() -> ParseService`

Creates a `ParseService` wired to the OpenDota client and match repository.

#### `export_service() -> ExportService`

Creates an `ExportService` wired to the hero, match, and chat wheel repositories.

## Dependencies

- `api.client.StratzClient`
- `api.opendota_client.OpenDotaClient`
- `database.Database`
- All repositories and services.

## Inputs

- Environment variables via `Config` (loaded by the clients).

## Outputs

- Wired service instances.

## Usage example

```python
from cli.factory import ServiceFactory

factory = ServiceFactory()
factory.db.init()
factory.db.migrate()
factory.hero_service().ensure_synced()
```
