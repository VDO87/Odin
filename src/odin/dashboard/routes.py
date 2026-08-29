"""Read-only dashboard routes."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
from uuid import uuid4

from odin.adapters.mt5.demo_session import reconcile_demo_session
from odin.adapters.mt5.demo_readonly_state import (
    read_demo_observation_audit,
    read_demo_readonly_state,
)
from odin.adapters.mt5.feed_quality import mt5_feed_quality_status
from odin.adapters.mt5.mock_bridge import mt5_bridge_status
from odin.adapters.mt5.market_feed import mt5_market_feed_status
from odin.adapters.mt5.symbol_mapping import mt5_symbol_mapping_status
from odin.contracts.events import OdinEvent, redact_for_audit
from odin.adapters.market_data.mock_market import market_status
from odin.dashboard.cockpit import cockpit_html
from odin.dashboard.tradedesk import tradedesk_html
from odin.trading.demo_execution_dashboard import demo_execution_dashboard_state
from odin.trading.autonomous_demo_state import (
    autonomous_demo_dashboard_state,
    request_control,
)
from odin.trading.replay import replay_trading_state
from odin.trading.replay_config import save_replay_config
from odin.trading.shadow_cycle import run_shadow_observation
from odin.shadow.replay import load_validated_bars, replay_shadow
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


_AUTONOMOUS_REPORT_FILENAMES = (
    "ODIN_AUTONOMOUS_DEMO_STATUS.md",
    "ODIN_AUTONOMOUS_DEMO_METRICS.json",
    "ODIN_AUTONOMOUS_DEMO_TRADES.jsonl",
    "ODIN_AUTONOMOUS_DEMO_INCIDENTS.md",
    "ODIN_AUTONOMOUS_DEMO_REPAIRS.md",
    "ODIN_HERMES_VS_REALITY.jsonl",
    "ODIN_RUNTIME_RATIONALIZATION_REPORT.md",
    "ODIN_AUTONOMOUS_DEMO_ACCEPTANCE_REPORT.md",
)


class DashboardRoutes:
    def __init__(
        self,
        *,
        log_path: str = "logs/odin_events.jsonl",
        sqlite_path: str = "runtime/odin.sqlite",
        public_cache_root: str | None = None,
        demo_execution_ledger_path: str = "/mnt/d/ODIN_LOCAL/runtime/demo_execution_ledger.jsonl",
        mt5_demo_state_path: str = "/mnt/d/ODIN_LOCAL/runtime/mt5_demo_readonly.json",
        autonomous_state_path: str = "/mnt/d/ODIN_LOCAL/state/autonomous_demo_state.json",
        autonomous_heartbeat_path: str = "/mnt/d/ODIN_LOCAL/state/autonomous_demo_heartbeat.json",
        autonomous_control_path: str = "/mnt/d/ODIN_LOCAL/state/autonomous_demo_control.json",
        autonomous_incidents_path: str = "/mnt/d/ODIN_LOCAL/state/autonomous_demo_incidents.jsonl",
        autonomous_report_root: str = "/mnt/d/ODIN_LOCAL/reports",
    ) -> None:
        self.log_path = log_path
        self.sqlite_path = sqlite_path
        self.public_cache_root = public_cache_root or os.environ.get(
            "ODIN_PUBLIC_DATA_CACHE_DIR", "/mnt/d/ODIN_LOCAL/cache/public"
        )
        self.demo_execution_ledger_path = demo_execution_ledger_path
        self.mt5_demo_state_path = mt5_demo_state_path
        self.autonomous_state_path = autonomous_state_path
        self.autonomous_heartbeat_path = autonomous_heartbeat_path
        self.autonomous_control_path = autonomous_control_path
        self.autonomous_incidents_path = autonomous_incidents_path
        self.autonomous_report_root = autonomous_report_root
        self.run_id = str(uuid4())
        self.logger = JsonlLogger(log_path)
        self.store = SQLiteStore(sqlite_path)
        self.store.initialize()

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
            payload = health_payload(
                {
                    "safe_to_trade": False,
                    "real_trading": False,
                }
            )
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

        if path == "/operations/autonomous-demo":
            payload = autonomous_demo_dashboard_state(
                state_path=self.autonomous_state_path,
                heartbeat_path=self.autonomous_heartbeat_path,
                incidents_path=self.autonomous_incidents_path,
                report_root=self.autonomous_report_root,
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/operations/autonomous-demo/reports":
            payload = self._autonomous_report_inventory()
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

        if path == "/trading/demo-execution":
            payload = demo_execution_dashboard_state(
                ledger_path=self.demo_execution_ledger_path,
                mt5_state_path=self.mt5_demo_state_path,
            )
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/trading/shadow-cycle":
            payload = run_shadow_observation()
            self._audit(DASHBOARD_STATE_SERVED, {"path": path})
            return 200, payload

        if path == "/shadow/intelligence":
            payload = self._shadow_intelligence()
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
                observation_frame_quality_status(
                    log_path=self.log_path, sqlite_path=self.sqlite_path
                )
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
        event_name = (
            "trading.replay_config.updated"
            if result["status"] == "OK"
            else "trading.replay_config.blocked"
        )
        self._audit(
            event_name,
            {
                "status": result["status"],
                "reason": result.get("reason", ""),
                "watchlist": result.get("watchlist", []),
            },
        )
        return (200 if result["status"] == "OK" else 400), result

    def configure_autonomous_demo_control(self, value: object) -> tuple[int, dict[str, object]]:
        """Persist PAUSE/SAFE_STOP/confirmed RESUME as a local operator request."""
        if not isinstance(value, dict):
            result = {
                "status": "BLOCKED",
                "reason": "operator_control_request_invalid",
                "execution_allowed": False,
                "safe_to_trade": False,
                "real_trading": False,
            }
        else:
            result = request_control(
                self.autonomous_control_path,
                action=str(value.get("action", "")),
                request_id=str(uuid4()),
                resume_confirmed=value.get("resume_confirmed") is True,
            )
        self._audit(
            "operations.autonomous_demo_control",
            {
                "status": result["status"],
                "action": value.get("action") if isinstance(value, dict) else "",
            },
        )
        return (200 if result["status"] == "ACCEPTED" else 400), result

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

    def _autonomous_report_inventory(self) -> dict[str, object]:
        root = Path(self.autonomous_report_root)
        reports: list[dict[str, object]] = []
        for filename in _AUTONOMOUS_REPORT_FILENAMES:
            path = root / filename
            try:
                stat = path.stat()
                available = path.is_file()
            except OSError:
                stat = None
                available = False
            reports.append(
                {
                    "filename": filename,
                    "available": available,
                    "size_bytes": stat.st_size if available and stat is not None else 0,
                    "modified_at_utc": (
                        datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()
                        if available and stat is not None
                        else None
                    ),
                }
            )
        available_reports = sum(item["available"] is True for item in reports)
        return {
            "status": "OK"
            if available_reports == len(_AUTONOMOUS_REPORT_FILENAMES)
            else "WARNING",
            "component": "autonomous_demo_report_inventory",
            "report_root": str(root),
            "available_reports": available_reports,
            "expected_reports": len(_AUTONOMOUS_REPORT_FILENAMES),
            "reports": reports,
            "read_only": True,
            "safe_to_trade": False,
            "real_trading": False,
            "execution_allowed": False,
        }

    def _operational_overview(self) -> dict[str, object]:
        """Return a read-only summary from already-persisted operational evidence.

        Dashboard reads must not rebuild mock observation frames or rerun Hermes.
        Those pipelines emit their own audit trails and made an old polling client
        recursively grow JSONL/SQLite.  The persistent RC2 supervisor is the live
        source for this compatibility endpoint.
        """
        autonomous = autonomous_demo_dashboard_state(
            state_path=self.autonomous_state_path,
            heartbeat_path=self.autonomous_heartbeat_path,
            incidents_path=self.autonomous_incidents_path,
            report_root=self.autonomous_report_root,
        )
        supervisor = _object_dict(autonomous.get("supervisor"))
        observed = _object_dict(supervisor.get("observed"))
        resources = _object_dict(observed.get("resources"))
        resource_snapshot = _object_dict(resources.get("snapshot"))
        market = _object_dict(autonomous.get("market"))
        risk = _object_dict(autonomous.get("risk"))
        decision = _object_dict(autonomous.get("decision"))
        execution = _object_dict(autonomous.get("execution"))
        heartbeat = _object_dict(autonomous.get("heartbeat"))
        reason_codes = supervisor.get("reason_codes", [])
        reasons = reason_codes if isinstance(reason_codes, list) else []
        supervisor_state = str(supervisor.get("state", "EXECUTION_PAUSED"))
        terminal_connected = observed.get("terminal_connected") is True
        account_mode = str(observed.get("account_mode", "UNKNOWN"))
        mt5_connected_demo = terminal_connected and account_mode == "DEMO"
        hermes_running = resource_snapshot.get("hermes_running") is True or (
            resource_snapshot.get("wsl_hermes_running") is True
        )
        ollama_running = resource_snapshot.get("ollama_running") is True
        market_fresh = market.get("data_freshness") == "FRESH"
        market_open = market.get("market_open") is True
        strategy_status = decision.get("decision", decision.get("status", "NO_TRADE"))

        return {
            "status": autonomous.get("status", "BLOCKED"),
            "component": "operations_overview",
            "mode": "LOCAL_ONLY",
            "read_only": True,
            "source": "persistent_autonomous_demo_state",
            "safety": {
                "safe_to_trade": False,
                "real_trading": False,
                "execution_allowed": False,
                "human_approval_required": False,
                "dashboard_configuration_writes_allowed": False,
            },
            "local_runtime": {
                "runtime_status": autonomous.get("status", "BLOCKED"),
                "hermes_status": "OK" if hermes_running else "DEGRADED",
                "hermes_operational_state": "READ_ONLY",
                "ollama_available": ollama_running,
                "local_models": [],
                "resource_guardian": resource_snapshot,
                "warnings": resources.get("warning_codes", []),
            },
            "observation": {
                "market_status": "OPEN" if market_open and market_fresh else supervisor_state,
                "market_provider": observed.get("broker", "UNKNOWN"),
                "observation_frame_status": market.get("data_freshness", "UNKNOWN"),
                "strategy_status": strategy_status,
                "risk_gate_status": risk.get("status", "BLOCK"),
            },
            "supervised_demo": {
                "observer": {
                    "status": "RUNNING" if heartbeat.get("fresh") is True else "DEGRADED",
                    "reason": reasons[0] if reasons else supervisor_state,
                    "execution_allowed": False,
                },
                "mt5": {
                    "status": "CONNECTED_DEMO_READ_ONLY"
                    if mt5_connected_demo
                    else "BLOCKED",
                    "reason": reasons[0] if reasons else supervisor_state,
                    "terminal_connection_attempted": "terminal_connected" in observed,
                    "kill_switch_engaged": observed.get("kill_switch_engaged", False),
                    "execution_allowed": False,
                },
                "mt5_observation": {
                    "status": "CONNECTED_DEMO_READ_ONLY"
                    if mt5_connected_demo
                    else "BLOCKED",
                    "as_of": supervisor.get("updated_at_utc", ""),
                    "market_status": "OPEN" if market_open and market_fresh else supervisor_state,
                    "market_as_of": market.get("normalized_event_time_utc", ""),
                    "positions_count": observed.get("positions_count", 0),
                    "execution_allowed": False,
                },
                "execution": execution,
            },
            "configuration": {
                "provider_policy": "local_first",
                "cloud_fallback_allowed": False,
                "automatic_code_application": False,
                "repository_code_application": False,
                "financial_data_policy": "read_only_observation",
                "changes": "Use a reviewed local config change; this endpoint is informational.",
            },
        }

    def _shadow_intelligence(self) -> dict[str, object]:
        """Expose P0 replay evidence only; this route cannot interact with a broker."""
        root = Path(os.environ.get("ODIN_LOCAL_ROOT", "/mnt/d/ODIN_LOCAL"))
        manifests = sorted(
            (root / "artifacts" / "market-data" / "EURUSD" / "M15").glob("*.manifest.json")
        )
        if not manifests:
            return {
                "status": "BLOCKED",
                "mode": "SHADOW",
                "reason": "validated_p0_dataset_unavailable",
                "execution_allowed": False,
                "safe_to_trade": False,
                "real_trading": False,
            }
        try:
            data = json.loads(manifests[-1].read_text(encoding="utf-8"))
            bars = load_validated_bars(artifact_root=root, dataset_hash=str(data["dataset_hash"]))
            replay = replay_shadow(bars)
            latest = replay["decisions"][-1] if replay["decisions"] else {}
            return {
                "status": "OK",
                "mode": "SHADOW_REPLAY",
                "latest": latest,
                "decisions_hash": replay["decisions_hash"],
                "execution_allowed": False,
                "safe_to_trade": False,
                "real_trading": False,
            }
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return {
                "status": "BLOCKED",
                "mode": "SHADOW",
                "reason": "validated_p0_dataset_invalid",
                "execution_allowed": False,
                "safe_to_trade": False,
                "real_trading": False,
            }

    def _audit(self, event_name: str, payload: dict[str, object]) -> None:
        event = OdinEvent.create(
            run_id=self.run_id,
            component="odin.dashboard",
            event=event_name,
            payload=payload,
        )
        self.logger.write(event)
        self.store.record_event(event)


def _object_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


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
