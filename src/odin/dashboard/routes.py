"""Read-only dashboard routes."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from odin.adapters.mt5.feed_quality import mt5_feed_quality_status
from odin.adapters.mt5.mock_bridge import mt5_bridge_status
from odin.adapters.mt5.market_feed import mt5_market_feed_status
from odin.adapters.mt5.symbol_mapping import mt5_symbol_mapping_status
from odin.contracts.events import OdinEvent
from odin.adapters.market_data.mock_market import market_status
from odin.core.market_watch import run_market_watch
from odin.core.smoke import run_runtime_smoke
from odin.data.feed_source_selector import feed_source_status
from odin.data.quality import data_quality_status
from odin.decision.intent import decision_intent
from odin.decision.observation_frame import observation_frame_status
from odin.decision.shadow_proposal import shadow_proposal
from odin.decision.strategy_status import strategy_status
from odin.contracts.events import (
    DASHBOARD_LOGS_TAIL_SERVED,
    DASHBOARD_REQUEST_RECEIVED,
    DASHBOARD_STATE_SERVED,
)
from odin.core.bootstrap import validate_runtime
from odin.dashboard.schemas import (
    dashboard_state_payload,
    data_quality_payload,
    decision_intent_payload,
    feed_source_payload,
    health_payload,
    hermes_summary_payload,
    hermes_status_payload,
    not_found_payload,
    market_status_payload,
    market_watch_payload,
    mt5_bridge_payload,
    mt5_feed_quality_payload,
    mt5_feed_payload,
    mt5_symbols_payload,
    observation_frame_payload,
    risk_status_payload,
    risk_gate_payload,
    runtime_smoke_payload,
    shadow_proposal_payload,
    strategy_status_payload,
    treasury_status_payload,
)
from odin.hermes.service import generate_hermes_summary
from odin.logging.jsonl_logger import JsonlLogger
from odin.risk.gate import risk_gate
from odin.storage.sqlite_store import SQLiteStore
from odin.treasury.engine import treasury_status

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

        if path == "/treasury/status":
            payload = treasury_status_payload(
                treasury_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/market/status":
            payload = market_status_payload(
                market_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/market/watch":
            payload = market_watch_payload(
                run_market_watch(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/data/quality":
            payload = data_quality_payload(
                data_quality_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/feed/source":
            payload = feed_source_payload(
                feed_source_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/observation/frame":
            payload = observation_frame_payload(
                observation_frame_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/strategy/status":
            payload = strategy_status_payload(
                strategy_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/decision/intent":
            payload = decision_intent_payload(
                decision_intent(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/risk/gate":
            payload = risk_gate_payload(
                risk_gate(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/shadow/proposal":
            payload = shadow_proposal_payload(
                shadow_proposal(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/mt5/bridge":
            payload = mt5_bridge_payload(
                mt5_bridge_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/mt5/symbols":
            payload = mt5_symbols_payload(
                mt5_symbol_mapping_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/mt5/feed":
            payload = mt5_feed_payload(
                mt5_market_feed_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/mt5/feed/quality":
            payload = mt5_feed_quality_payload(
                mt5_feed_quality_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/runtime/smoke":
            payload = runtime_smoke_payload(
                run_runtime_smoke(log_path=self.log_path, sqlite_path=self.sqlite_path)
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
