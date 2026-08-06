from datetime import datetime, timezone
from typing import Any


def parse_timestamp(value: Any) -> str:
    """Normalize a timestamp value into an ISO 8601 UTC string.

    Supports string values (returned as-is), Unix timestamps as int/float,
    and falls back to the current UTC time for unsupported values.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()
