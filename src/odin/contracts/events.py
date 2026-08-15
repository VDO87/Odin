"""Event contracts for JSONL and SQLite audit records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import os
from typing import Any
from uuid import uuid4

from odin.contracts.state import OperationalMode


BOOTSTRAP_STARTED = "odin.bootstrap.started"
BOOTSTRAP_COMPLETED = "odin.bootstrap.completed"
VALIDATE_STARTED = "odin.validate.started"
VALIDATE_COMPLETED = "odin.validate.completed"
RISK_PLACEHOLDER_READY_BLOCKING = "risk.placeholder.ready_blocking"
HERMES_PERMISSIONS_READ_ONLY = "hermes.permissions.read_only"
STORAGE_SQLITE_INITIALIZED = "storage.sqlite.initialized"
LOGGING_JSONL_READY = "logging.jsonl.ready"
SECURITY_REAL_TRADING_BLOCKED = "security.real_trading.blocked"
DASHBOARD_SERVER_STARTED = "dashboard.server.started"
DASHBOARD_SERVER_STOPPED = "dashboard.server.stopped"
DASHBOARD_REQUEST_RECEIVED = "dashboard.request.received"
DASHBOARD_STATE_SERVED = "dashboard.state.served"
DASHBOARD_LOGS_TAIL_SERVED = "dashboard.logs_tail.served"
HERMES_SUMMARY_STARTED = "hermes.summary.started"
HERMES_SUMMARY_COMPLETED = "hermes.summary.completed"
HERMES_RECOMMENDATION_GENERATED = "hermes.recommendation.generated"
HERMES_READ_ONLY_GUARD_CONFIRMED = "hermes.read_only.guard_confirmed"
HERMES_SUPERVISOR_CYCLE_STARTED = "hermes.supervisor.cycle.started"
HERMES_SUPERVISOR_CYCLE_COMPLETED = "hermes.supervisor.cycle.completed"
HERMES_SUPERVISOR_CYCLE_DEGRADED = "hermes.supervisor.cycle.degraded"
HERMES_AGENT_CATALOG_SYNCED = "hermes.agent_catalog.synced"
HERMES_SKILL_CATALOG_SYNCED = "hermes.skill_catalog.synced"
HERMES_GOAL_ENGINE_UPDATED = "hermes.goal_engine.updated"
HERMES_MEMORY_UPDATED = "hermes.memory.updated"
TREASURY_STATUS_REQUESTED = "treasury.status.requested"
TREASURY_STATUS_GENERATED = "treasury.status.generated"
TREASURY_TRANSFER_BLOCKED = "treasury.transfer.blocked"
TREASURY_TAX_RESERVE_CALCULATED = "treasury.tax.reserve.calculated"
TREASURY_READ_ONLY_GUARD_CONFIRMED = "treasury.read_only.guard_confirmed"
MARKET_MOCK_SNAPSHOT_GENERATED = "market.mock.snapshot.generated"
MARKET_MOCK_CANDLES_GENERATED = "market.mock.candles.generated"
MARKET_QUALITY_CHECKED = "market.quality.checked"
MARKET_STATUS_GENERATED = "market.status.generated"
MARKET_EXECUTION_BLOCKED = "market.execution.blocked"
MARKET_WATCH_STARTED = "market_watch.started"
MARKET_WATCH_SNAPSHOT_LOADED = "market_watch.snapshot_loaded"
MARKET_WATCH_QUALITY_CHECKED = "market_watch.quality_checked"
MARKET_WATCH_COMPLETED = "market_watch.completed"
MARKET_WATCH_EXECUTION_BLOCKED = "market_watch.execution.blocked"
MARKET_WATCH_DECISION_BLOCKED = "market_watch.decision.blocked"
DATA_QUALITY_STARTED = "data_quality.started"
DATA_QUALITY_GATE_CHECKED = "data_quality.gate.checked"
DATA_QUALITY_COMPLETED = "data_quality.completed"
DATA_QUALITY_BLOCKED = "data_quality.blocked"
DATA_QUALITY_DECISION_BLOCKED = "data_quality.decision.blocked"
STRATEGY_STATUS_REQUESTED = "strategy.status.requested"
STRATEGY_BASELINE_LOADED = "strategy.baseline.loaded"
STRATEGY_OBSERVATION_COMPLETED = "strategy.observation.completed"
STRATEGY_DECISION_BLOCKED = "strategy.decision.blocked"
STRATEGY_EXECUTION_BLOCKED = "strategy.execution.blocked"
DECISION_INTENT_REQUESTED = "decision.intent.requested"
DECISION_INTENT_SKELETON_CREATED = "decision.intent.skeleton.created"
DECISION_INTENT_BLOCKED = "decision.intent.blocked"
DECISION_RISK_APPROVAL_BLOCKED = "decision.risk_approval.blocked"
DECISION_EXECUTION_BLOCKED = "decision.execution.blocked"
RISK_GATE_REQUESTED = "risk.gate.requested"
RISK_GATE_LOADED = "risk.gate.loaded"
RISK_GATE_BLOCKED = "risk.gate.blocked"
RISK_GATE_RISK_APPROVAL_BLOCKED = "risk.gate.risk_approval.blocked"
RISK_GATE_EXECUTION_BLOCKED = "risk.gate.execution.blocked"
SHADOW_PROPOSAL_REQUESTED = "shadow.proposal.requested"
SHADOW_PROPOSAL_SKELETON_CREATED = "shadow.proposal.skeleton.created"
SHADOW_PROPOSAL_BLOCKED = "shadow.proposal.blocked"
SHADOW_PROPOSAL_EXECUTION_BLOCKED = "shadow.proposal.execution.blocked"
SHADOW_PROPOSAL_RISK_BLOCKED = "shadow.proposal.risk.blocked"
RUNTIME_SMOKE_REQUESTED = "runtime.smoke.requested"
RUNTIME_SMOKE_MODULE_CHECKED = "runtime.smoke.module.checked"
RUNTIME_SMOKE_PASS = "runtime.smoke.pass"
RUNTIME_SMOKE_FAIL = "runtime.smoke.fail"
RUNTIME_SMOKE_SAFE_STATE_CONFIRMED = "runtime.smoke.safe_state.confirmed"
MT5_BRIDGE_REQUESTED = "mt5.bridge.requested"
MT5_BRIDGE_MOCK_LOADED = "mt5.bridge.mock.loaded"
MT5_BRIDGE_REAL_IMPORT_BLOCKED = "mt5.bridge.real_import.blocked"
MT5_BRIDGE_EXECUTION_BLOCKED = "mt5.bridge.execution.blocked"
MT5_BRIDGE_STATUS_REPORTED = "mt5.bridge.status.reported"
MT5_SYMBOLS_REQUESTED = "mt5.symbols.requested"
MT5_SYMBOLS_MOCK_LOADED = "mt5.symbols.mock.loaded"
MT5_SYMBOLS_MAPPING_REPORTED = "mt5.symbols.mapping.reported"
MT5_SYMBOLS_EXECUTION_BLOCKED = "mt5.symbols.execution.blocked"
MT5_SYMBOLS_NON_ASSET_DETECTED = "mt5.symbols.non_mt5_asset.detected"
MT5_FEED_REQUESTED = "mt5.feed.requested"
MT5_FEED_MOCK_LOADED = "mt5.feed.mock.loaded"
MT5_FEED_TICK_GENERATED = "mt5.feed.tick.generated"
MT5_FEED_EXECUTION_BLOCKED = "mt5.feed.execution.blocked"
MT5_FEED_STATUS_REPORTED = "mt5.feed.status.reported"
MT5_FEED_QUALITY_REQUESTED = "mt5.feed_quality.requested"
MT5_FEED_QUALITY_GATE_CHECKED = "mt5.feed_quality.gate.checked"
MT5_FEED_QUALITY_PASS = "mt5.feed_quality.pass"
MT5_FEED_QUALITY_FAIL = "mt5.feed_quality.fail"
MT5_FEED_QUALITY_EXECUTION_BLOCKED = "mt5.feed_quality.execution.blocked"
FEED_SOURCE_REQUESTED = "feed.source.requested"
FEED_SOURCE_MT5_MOCK_SELECTED = "feed.source.mt5_mock.selected"
FEED_SOURCE_MARKET_DATA_MOCK_AVAILABLE = "feed.source.market_data_mock.available"
FEED_SOURCE_DECISION_BLOCKED = "feed.source.decision.blocked"
FEED_SOURCE_STATUS_REPORTED = "feed.source.status.reported"
OBSERVATION_FRAME_REQUESTED = "observation.frame.requested"
OBSERVATION_FRAME_BUILT = "observation.frame.built"
OBSERVATION_FRAME_DECISION_BLOCKED = "observation.frame.decision.blocked"
OBSERVATION_FRAME_EXECUTION_BLOCKED = "observation.frame.execution.blocked"
OBSERVATION_FRAME_STATUS_REPORTED = "observation.frame.status.reported"
OBSERVATION_FRAME_QUALITY_REQUESTED = "observation.frame_quality.requested"
OBSERVATION_FRAME_QUALITY_GATE_CHECKED = "observation.frame_quality.gate.checked"
OBSERVATION_FRAME_QUALITY_PASS = "observation.frame_quality.pass"
OBSERVATION_FRAME_QUALITY_FAIL = "observation.frame_quality.fail"
OBSERVATION_FRAME_QUALITY_DECISION_BLOCKED = "observation.frame_quality.decision.blocked"
OBSERVATION_FRAME_QUALITY_EXECUTION_BLOCKED = "observation.frame_quality.execution.blocked"
STRATEGY_CONTEXT_SNAPSHOT_REQUESTED = "strategy.context_snapshot.requested"
STRATEGY_CONTEXT_SNAPSHOT_BUILT = "strategy.context_snapshot.built"
STRATEGY_CONTEXT_SNAPSHOT_INVALID = "strategy.context_snapshot.invalid"
STRATEGY_CONTEXT_SNAPSHOT_DECISION_BLOCKED = "strategy.context_snapshot.decision.blocked"
STRATEGY_CONTEXT_SNAPSHOT_EXECUTION_BLOCKED = "strategy.context_snapshot.execution.blocked"
STRATEGY_CONTEXT_SNAPSHOT_QUALITY_REQUESTED = "strategy.context_snapshot_quality.requested"
STRATEGY_CONTEXT_SNAPSHOT_QUALITY_PASS = "strategy.context_snapshot_quality.pass"
STRATEGY_CONTEXT_SNAPSHOT_QUALITY_BLOCKED = "strategy.context_snapshot_quality.blocked"
STRATEGY_CONTEXT_SNAPSHOT_QUALITY_DECISION_BLOCKED = "strategy.context_snapshot_quality.decision.blocked"


@dataclass(frozen=True)
class OdinEvent:
    run_id: str
    corr_id: str
    component: str
    event: str
    severity: str
    mode: str = OperationalMode.OFF_SAFE.value
    symbol: str | None = None
    safe_to_trade: bool = False
    reason: str = "fail_closed"
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        component: str,
        event: str,
        severity: str = "INFO",
        corr_id: str | None = None,
        reason: str = "fail_closed",
        payload: dict[str, Any] | None = None,
    ) -> "OdinEvent":
        return cls(
            run_id=run_id,
            corr_id=corr_id or str(uuid4()),
            component=component,
            event=event,
            severity=severity,
            reason=reason,
            payload=payload or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "corr_id": self.corr_id,
            "component": self.component,
            "event": self.event,
            "severity": self.severity,
            "mode": self.mode,
            "symbol": self.symbol,
            "safe_to_trade": self.safe_to_trade,
            "reason": self.reason,
            "payload": _redact_payload(self.payload),
        }


def _redact_payload(value: Any) -> Any:
    """Remove local access material before an event reaches JSONL or SQLite."""
    return redact_for_audit(value)


def redact_for_audit(value: Any) -> Any:
    """Sanitize a value before it reaches any local operator-facing surface."""
    return _redact_value(value, _local_access_values())


def _local_access_values() -> set[str]:
    names = (
        "ODIN_MT5_LOGIN", "ODIN_MT5_PASSWORD", "ODIN_MT5_SERVER",
        "ODIN_OANDA_PRACTICE_TOKEN", "ODIN_OANDA_PRACTICE_ACCOUNT_ID",
    )
    return {os.environ[name] for name in names if os.environ.get(name)}


def _redact_value(value: Any, secrets: set[str]) -> Any:
    if isinstance(value, str):
        return "[REDACTED]" if any(secret in value for secret in secrets) else value
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if _sensitive_key(str(key)) else _redact_value(item, secrets)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item, secrets) for item in value]
    if isinstance(value, tuple):
        return [_redact_value(item, secrets) for item in value]
    return value


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in ("password", "secret", "token", "credential", "api_key", "access_key"))
