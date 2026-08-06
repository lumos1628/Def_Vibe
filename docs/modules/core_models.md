# `core/models.py` — Domain Models

## Purpose

Defines typed dataclasses for key domain concepts. These models document the data shape and can be used gradually to replace raw dictionaries in services and repositories.

## Public classes

### `Hero`

Represents a Dota 2 hero.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Hero ID |
| `display_name` | `str` | Human-readable name |
| `short_name` | `str` | Internal short name |

### `ChatWheel`

Represents a chat wheel entry.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Chat wheel ID |
| `name` | `str` | Internal name |
| `label` | `str` | Display label |
| `message` | `str` | Message text |
| `all_chat` | `bool` | Whether it is sent to all chat |

### `Match`

Represents a discovered rampage match.

| Field | Type | Description |
|-------|------|-------------|
| `match_id` | `int` | Dota 2 match ID |
| `hero_id` | `int` | Hero ID |
| `played_at` | `datetime` | Match start time |
| `steam_account_id` | `int` | Player account ID |
| `parsed` | `bool` | Legacy parse flag |
| `has_replay_data` | `bool` | Whether replay data exists |
| `data_verified` | `bool` | Whether OpenDota verified the match |
| `unparseable` | `bool` | Whether the match cannot be parsed |
| `parse_status` | `str` | Current parse state |

### `OpenDotaMatchData`

Thin wrapper around raw OpenDota match JSON.

| Method | Description |
|--------|-------------|
| `get_players()` | Returns the `players` array |
| `get_chat()` | Returns the `chat` array |
| `get_start_time()` | Returns `start_time` |

### `ExportRecord`

Represents an entry in the export log.

| Field | Type | Description |
|-------|------|-------------|
| `match_id` | `int` | Exported match ID |
| `exported_at` | `datetime` | Export timestamp |
| `output_path` | `str` | Output directory |

## Dependencies

- Standard library: `dataclasses`, `datetime`, `typing`

## Usage example

```python
from core.models import Hero, Match
from datetime import datetime, timezone

hero = Hero(id=86, display_name="Rubick", short_name="rubick")
match = Match(
    match_id=123456789,
    hero_id=hero.id,
    played_at=datetime.now(timezone.utc),
    steam_account_id=987654321,
)
```
