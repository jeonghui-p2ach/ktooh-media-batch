from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any


def to_utc_naive(value: Any, default: datetime | None = None) -> datetime | None:
    """Normalize any datetime-like value to a UTC-normalized naive datetime.
    
    - If aware (with tzinfo), convert to UTC and then remove tzinfo.
    - If naive, assume it's already UTC (as per project policy) and return as-is.
    - If date, combine with midnight.
    - If ISO string, parse and apply the same logic.
    """
    if value is None:
        return default

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, datetime.min.time())
    elif isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return default
    else:
        return default

    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt.replace(tzinfo=None)
