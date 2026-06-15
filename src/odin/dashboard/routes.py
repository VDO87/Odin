"""Read-only dashboard routes."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from odin.contracts.events import OdinEvent
from odin.contracts.events import (
    DASHBOARD_LOGS_TAIL_SERVED,
    DASHBOARD_REQUEST_RECEIVED,
    DASHBOARD_STATE_SERVED,
)
from odin.core.bootstrap import validate_runtime
from odin.dashboard.schemas import (
    dashboard_state_payload,
    health_payload,
    hermes_summary_payload,
    hermes_status_payload,
    not_found_payload,
    risk_status_payload,
)
from odin.hermes.service import generate_hermes_summary
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore

class DashboardRoutes:
    def __init__(
        self,
        *,
        log_path: str = "logs/odin_events.jsonl",
        sqlite_path: str = "runtime/odin.sqlite",
    ) -> None:
        self.log_path = log_path
        self.sqlite_path = sqlite_path
        self.run_id = str(uuid4())
        self.logger = JsonlLogger(log_path)
        self.store = SQLiteStore(sqlite_path)

    def serve(self, path: str) -> tuple[int, dict[str, object]]:
        if path == "/logs/tail":
            payload = self.logs_tail()
            self._audit(DASHBOARD_REQUEST_RECEIVED, {"path": path})
            self._audit(DASHBOARD_LOGS_TAIL_SERVED, {"path": path, "count": len(payload["lines"])})
            return 200, payload

        self._audit(DASHBOARD_REQUEST_RECEIVED, {"path": path})

        if path == "/health":
            state = self._state()
            payload = health_payload(state)
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/state":
            payload = dashboard_state_payload(self._state())
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/risk/status":
            payload = risk_status_payload()
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/hermes/status":
            payload = hermes_status_payload()
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/hermes/summary":
            payload = hermes_summary_payload(
                generate_hermes_summary(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        return 404, not_found_payload(path)

    def logs_tail(self, *, limit: int = 20) -> dict[str, object]:
        path = Path(self.log_path)
        if not path.exists():
            return {
                "status": "OK",
                "lines": [],
                "reason": "log file not found yet",
            }

        raw_lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
        lines: list[object] = []
        for line in raw_lines:
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                lines.append({"raw": line, "parse_error": True})
        return {
            "status": "OK",
            "lines": lines,
        }

    def _state(self) -> dict[str, object]:
        return validate_runtime(log_path=self.log_path, sqlite_path=self.sqlite_path)

    def _audit(self, event_name: str, payload: dict[str, object]) -> None:
        event = OdinEvent.create(
            run_id=self.run_id,
            component="odin.dashboard",
            event=event_name,
            payload=payload,
        )
        self.logger.write(event)
        self.store.initialize()
        self.store.record_event(event)
