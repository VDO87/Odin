from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class NetworkStatus:
    online: bool
    failures: int
    threshold_reached: bool


class NetworkMonitor:
    def __init__(self, failure_threshold: int = 3) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self._failures = 0
        self._online = True

    def update(self, online: bool) -> NetworkStatus:
        self._online = online
        if online:
            self._failures = 0
        else:
            self._failures += 1
        return NetworkStatus(
            online=self._online,
            failures=self._failures,
            threshold_reached=self._failures >= self.failure_threshold,
        )
