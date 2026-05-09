from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def isoformat_utc(value: datetime) -> str:
    return ensure_utc(value).isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    return ensure_utc(parsed)


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"
