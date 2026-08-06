# `core/time.py` — Time Utilities

## Purpose

Shared utilities for parsing and normalizing timestamp values returned by external APIs.

This module removes the duplication of `_parse_timestamp()` that previously existed in multiple discovery services.

## Public functions

### `parse_timestamp(value: Any) -> str`

Normalizes a timestamp into an ISO 8601 UTC string.

- If `value` is a string, returns it as-is.
- If `value` is an `int` or `float`, treats it as a Unix timestamp and converts it.
- For any other value, returns the current UTC time.

## Dependencies

- Standard library: `datetime`, `typing`

## Inputs

- A timestamp value from an API response (string, int, float, or unknown).

## Outputs

- An ISO 8601 formatted string.

## Usage example

```python
from core.time import parse_timestamp

print(parse_timestamp("2026-08-01T12:00:00+00:00"))
print(parse_timestamp(1690891200))
```
