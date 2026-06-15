"""Event contracts for JSONL and SQLite audit records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
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
            "payload": self.payload,
        }
