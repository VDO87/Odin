"""Read-only dashboard routes."""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from odin.adapters.brokers.isolated_observer import observer_status
from odin.adapters.mt5.demo_session import reconcile_demo_session
from odin.adapters.mt5.demo_readonly_state import read_demo_observation_audit, read_demo_readonly_state
from odin.adapters.mt5.feed_quality import mt5_feed_quality_status
from odin.adapters.mt5.mock_bridge import mt5_bridge_status
from odin.adapters.mt5.market_feed import mt5_market_feed_status
from odin.adapters.mt5.symbol_mapping import mt5_symbol_mapping_status
from odin.contracts.events import OdinEvent, redact_for_audit
from odin.adapters.market_data.mock_market import market_status
from odin.dashboard.cockpit import cockpit_html
from odin.dashboard.tradedesk import tradedesk_html
from odin.trading.replay import replay_trading_state
from odin.trading.replay_config import save_replay_config
from odin.trading.shadow_cycle import run_shadow_observation
from odin.core.market_watch import run_market_watch
from odin.core.smoke import run_runtime_smoke
from odin.data.feed_source_selector import feed_source_status
from odin.data.canonical_candle_history import canonical_candle_history_status
from odin.data.public_observation import public_observation_cache_status
from odin.data.quality import data_quality_status
from odin.decision.intent import decision_intent
from odin.decision.observation_frame import observation_frame_status
from odin.decision.observation_frame_quality import observation_frame_quality_status
from odin.decision.shadow_proposal import shadow_proposal
from odin.decision.strategy_status import strategy_status
from odin.decision.strategy_context_snapshot import strategy_context_snapshot_status
from odin.decision.strategy_context_snapshot_diff import strategy_context_snapshot_diff_status
from odin.decision.strategy_context_snapshot_quality import strategy_context_snapshot_quality_status
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
    operational_overview_payload,
    feed_source_payload,
    health_payload,
    hermes_summary_payload,
    hermes_runtime_payload,
    hermes_status_payload,
    not_found_payload,
    market_status_payload,
    market_watch_payload,
    mt5_bridge_payload,
    mt5_feed_quality_payload,
    mt5_feed_payload,
    mt5_symbols_payload,
    observation_frame_payload,
    observation_frame_quality_payload,
    risk_status_payload,
    risk_gate_payload,
    runtime_smoke_payload,
    shadow_proposal_payload,
    strategy_status_payload,
    strategy_context_snapshot_payload,
    strategy_context_snapshot_diff_payload,
    strategy_context_snapshot_quality_payload,
    treasury_status_payload,
)
from odin.hermes.service import generate_hermes_summary
from odin.hermes.supervisor import run_hermes_supervisor
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
        public_cache_root: str | None = None,
    ) -> None:
        self.log_path = log_path
        self.sqlite_path = sqlite_path
        self.public_cache_root = public_cache_root or os.environ.get(
            "ODIN_PUBLIC_DATA_CACHE_DIR", "/mnt/d/ODIN_LOCAL/cache/public"
        )
        self.run_id = str(uuid4())
        self.logger = JsonlLogger(log_path)
        self.store = SQLiteStore(sqlite_path)

    def serve(self, path: str) -> tuple[int, dict[str, object]]:
        if path == "/logs/tail":
            payload = self.logs_tail()
            self._audit(DASHBOARD_REQUEST_RECEIVED, {"path": path})
            lines = payload.get("lines", [])
            count = len(lines) if isinstance(lines, list) else 0
            self._audit(DASHBOARD_LOGS_TAIL_SERVED, {"path": path, "count": count})
            return 200, payload

        self._audit(DASHBOARD_REQUEST_RECEIVED, {"path": path})

        if path == "/health":
            state = self._state()
            payload = health_payload(state)
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/operations/overview":
            payload = self._operational_overview()
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/operations/events":
            payload = self.events_summary()
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/data/public":
            payload = public_observation_cache_status(self.public_cache_root)
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/data/history/canonical":
            payload = canonical_candle_history_status(
                artifact_root=os.environ.get("ODIN_LOCAL_ROOT", "/mnt/d/ODIN_LOCAL")
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/trading/replay":
            payload = replay_trading_state()
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/trading/shadow-cycle":
            payload = run_shadow_observation()
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

        if path == "/hermes/runtime":
            payload = hermes_runtime_payload(
                run_hermes_supervisor(log_path=self.log_path, sqlite_path=self.sqlite_path)
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

        if path == "/observation/frame/quality":
            payload = observation_frame_quality_payload(
                observation_frame_quality_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/strategy/context/snapshot":
            payload = strategy_context_snapshot_payload(
                strategy_context_snapshot_status(
                    log_path=self.log_path,
                    sqlite_path=self.sqlite_path,
                )
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/strategy/context/snapshot/quality":
            payload = strategy_context_snapshot_quality_payload(
                strategy_context_snapshot_quality_status(
                    log_path=self.log_path,
                    sqlite_path=self.sqlite_path,
                )
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/strategy/context/snapshot/diff":
            snapshot = strategy_context_snapshot_status(
                log_path=self.log_path,
                sqlite_path=self.sqlite_path,
            )
            payload = strategy_context_snapshot_diff_payload(
                strategy_context_snapshot_diff_status(
                    before_snapshot=snapshot,
                    after_snapshot=dict(snapshot),
                )
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

        if path == "/mt5/demo/session":
            payload = reconcile_demo_session("/mnt/d/ODIN_LOCAL/runtime/mt5_demo_session.json")
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/mt5/demo/observation":
            payload = read_demo_readonly_state()
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/mt5/demo/audit":
            payload = read_demo_observation_audit()
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

    def configure_replay(self, value: object) -> tuple[int, dict[str, object]]:
        """Persist a constrained replay preference; it never enables execution."""
        result = save_replay_config(value)
        event_name = "trading.replay_config.updated" if result["status"] == "OK" else "trading.replay_config.blocked"
        self._audit(event_name, {"status": result["status"], "reason": result.get("reason", ""), "watchlist": result.get("watchlist", [])})
        return (200 if result["status"] == "OK" else 400), result

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
                parsed = json.loads(line)
                lines.append(redact_for_audit(parsed))
            except json.JSONDecodeError:
                lines.append({"raw": "[REDACTED_UNPARSEABLE_LOG_LINE]", "parse_error": True})
        return {
            "status": "OK",
            "lines": lines,
        }

    def events_summary(self) -> dict[str, object]:
        """Classify recent audit events for a human operator, without mutation."""
        raw = self.logs_tail(limit=50).get("lines", [])
        events = [line for line in raw if isinstance(line, dict)] if isinstance(raw, list) else []
        alerts = [event for event in events if _is_alert(event)]
        return {
            "status": "OK",
            "component": "operations_events",
            "read_only": True,
            "events_count": len(events),
            "alerts_count": len(alerts),
            "alerts": [_event_view(event) for event in alerts[-20:]],
            "recent_events": [_event_view(event) for event in events[-20:]],
        }

    def _state(self) -> dict[str, object]:
        return validate_runtime(log_path=self.log_path, sqlite_path=self.sqlite_path)

    def cockpit_html(self) -> str:
        return cockpit_html()

    def tradedesk_html(self) -> str:
        return tradedesk_html()

    def _operational_overview(self) -> dict[str, object]:
        """Return one read-only, human-oriented local-first operations view."""
        return operational_overview_payload(
            state=self._state(),
            hermes=run_hermes_supervisor(
                log_path=self.log_path,
                sqlite_path=self.sqlite_path,
            ),
            market=market_status(log_path=self.log_path, sqlite_path=self.sqlite_path),
            observation=observation_frame_status(
                log_path=self.log_path,
                sqlite_path=self.sqlite_path,
            ),
            strategy=strategy_status(log_path=self.log_path, sqlite_path=self.sqlite_path),
            risk=risk_gate(log_path=self.log_path, sqlite_path=self.sqlite_path),
            observer=observer_status(),
            mt5=reconcile_demo_session("/mnt/d/ODIN_LOCAL/runtime/mt5_demo_session.json"),
            mt5_observation=read_demo_readonly_state(),
        )

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


def _is_alert(event: dict[str, object]) -> bool:
    severity = str(event.get("severity", "INFO")).upper()
    name = str(event.get("event", "")).lower()
    return severity in {"ERROR", "WARNING", "CRITICAL"} or name.endswith(".fail")


def _event_view(event: dict[str, object]) -> dict[str, object]:
    name = str(event.get("event", "unknown"))
    severity = str(event.get("severity", "INFO")).upper()
    return {
        "timestamp": event.get("timestamp", ""),
        "component": event.get("component", "unknown"),
        "event": name,
        "severity": severity,
        "reason": event.get("reason", ""),
        "next_safe_action": _next_safe_action(name, severity),
    }


def _next_safe_action(name: str, severity: str) -> str:
    lowered = name.lower()
    if lowered.endswith(".fail") or severity in {"ERROR", "CRITICAL"}:
        return "Inspect event payload and run the bounded smoke before retrying."
    if "degraded" in lowered or severity == "WARNING":
        return "Inspect provider or Hermes status; keep execution blocked."
    if "blocked" in lowered:
        return "No action required: the safety guard is working as designed."
    return "Review context in the raw event log."
