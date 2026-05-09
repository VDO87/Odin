from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any

from shared.utils import utc_now


@dataclass(slots=True)
class CacheEntry:
    value: Any
    expires_at_utc: datetime


class TTLCache:
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Any | None:
        now = utc_now()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.expires_at_utc < now:
                self._evictions += 1
                self._misses += 1
                self._entries.pop(key, None)
                return None
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, *, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        expires_at_utc = utc_now() + timedelta(seconds=ttl_seconds)
        with self._lock:
            self._entries[key] = CacheEntry(value=value, expires_at_utc=expires_at_utc)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "entries": len(self._entries),
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
            }
