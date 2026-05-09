from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from threading import Lock

from shared.utils import utc_now


class FixedWindowRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, list] = defaultdict(list)
        self._lock = Lock()

    def allow(self, key: str, *, max_calls: int, window_seconds: int) -> bool:
        if max_calls <= 0:
            return False
        now = utc_now()
        window_start = now - timedelta(seconds=window_seconds)
        with self._lock:
            events = [event for event in self._events[key] if event >= window_start]
            if len(events) >= max_calls:
                self._events[key] = events
                return False
            events.append(now)
            self._events[key] = events
            return True

    def calls_in_window(self, key: str, *, window_seconds: int) -> int:
        now = utc_now()
        window_start = now - timedelta(seconds=window_seconds)
        with self._lock:
            events = [event for event in self._events[key] if event >= window_start]
            self._events[key] = events
            return len(events)
