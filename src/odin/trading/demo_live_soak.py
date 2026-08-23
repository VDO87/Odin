"""Bounded pre-CANARY supervision for ODIN DEMO LIVE SOAK RC1.

This module has no MT5 dependency and cannot submit an order.  It evaluates
sanitized observations, persists bounded soak evidence and stops before the
first CANARY until the separate human-gated execution service is invoked.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
import json
from pathlib import Path
import time


EXPECTED_BROKER = "OANDA TMS Brokers S.A."
EXPECTED_SERVER = "OANDATMS-MT5"
EXPECTED_TERMINAL = r"C:\Program Files\OANDA TMS MT5 Terminal"
EXPECTED_SYMBOL = "EURUSD"
KNOWN_EXECUTION_ERRORS = frozenset(
    {
        "DISCONNECTED",
        "MARKET_CLOSED",
        "INVALID_VOLUME",
        "INVALID_STOPS",
        "NO_MONEY",
        "PRICE_CHANGED",
        "REQUOTE",
        "ORDER_REJECTED",
        "TIMEOUT",
        "FILLING_MODE",
        "TRADE_DISABLED",
        "UNKNOWN_RESULT",
        "DUPLICATE",
        "RECONCILIATION_MISMATCH",
    }
)
_IMMEDIATE_RISK_STOPS = frozenset(
    {
        "kill_switch_engaged",
        "daily_demo_loss_limit",
        "demo_drawdown_limit",
        "future_market_timestamp",
        "clock_skew_detected",
        "stale_data",
        "stale_data_threshold_exceeded",
        "excessive_spread",
    }
)
_IDENTITY_HARD_BLOCKS = frozenset(
    {
        "account_identity_hard_block",
        "broker_identity_hard_block",
        "server_identity_hard_block",
        "terminal_identity_hard_block",
    }
)


@dataclass(frozen=True)
class SoakLimits:
    max_trades: int = 5
    max_duration_seconds: int = 6 * 60 * 60
    cycle_interval_seconds: int = 60
    max_cycles: int = 360
    max_same_failure: int = 2

    def __post_init__(self) -> None:
        if not 1 <= self.max_trades <= 5:
            raise ValueError("max_trades_must_be_between_1_and_5")
        if not 1 <= self.max_duration_seconds <= 6 * 60 * 60:
            raise ValueError("max_duration_must_not_exceed_six_hours")
        if self.cycle_interval_seconds < 30:
            raise ValueError("cycle_interval_must_prevent_busy_loop")
        if self.max_cycles < 1:
            raise ValueError("max_cycles_must_be_positive")
        if self.max_same_failure != 2:
            raise ValueError("same_failure_limit_must_remain_two")


@dataclass(frozen=True)
class SoakCycleEvidence:
    observed_at_utc: str
    account_mode: str
    broker: str
    server: str
    terminal_path: str
    terminal_connected: bool
    terminal_trade_allowed: bool
    account_trade_allowed: bool
    account_trade_expert: bool
    symbol: str
    trade_mode: int
    data_fresh: bool
    time_normalization_valid: bool
    normalized_event_time_utc: str | None
    data_age_seconds: float | None
    spread_price: float
    spread_points: float
    spread_limit_price: float
    spread_limit_points: float
    reconciliation_status: str
    risk_status: str
    risk_reason_codes: tuple[str, ...]
    kill_switch_engaged: bool
    position_count: int
    position_reconciled: bool
    pending_execution: bool
    proposal_duplicate: bool
    proposal_available: bool
    no_trade: bool
    broker_submission_called: bool = False
    execution_error: str | None = None
    order_filled: bool = False
    order_rejected: bool = False
    reconnect_time_seconds: float | None = None
    slippage_points: float | None = None
    execution_latency_ms: float | None = None
    realized_pnl: float = 0.0
    floating_pnl: float = 0.0
    drawdown_demo_percent: float = 0.0
    margin: float | None = None
    free_margin: float | None = None
    daily_loss: float = 0.0


@dataclass(frozen=True)
class SoakCycleDecision:
    status: str
    reason_codes: tuple[str, ...]
    action: str
    stop: bool
    broker_action_allowed: bool = False


@dataclass
class SoakMetrics:
    started_at_utc: str
    ended_at_utc: str | None = None
    status: str = "RUNNING_PRE_CANARY"
    cycles: int = 0
    fresh_data_cycles: int = 0
    blocked_cycles: int = 0
    no_trade_count: int = 0
    trade_proposals: int = 0
    risk_block_count: int = 0
    orders_submitted: int = 0
    orders_filled: int = 0
    orders_rejected: int = 0
    duplicates_prevented: int = 0
    reconciliation_errors: int = 0
    mt5_disconnects: int = 0
    exceptions: int = 0
    self_repairs: int = 0
    failed_repairs: int = 0
    last_spread_price: float | None = None
    last_spread_points: float | None = None
    last_data_age_seconds: float | None = None
    reconnect_time_seconds: float | None = None
    slippage_points: float | None = None
    execution_latency_ms: float | None = None
    realized_pnl: float = 0.0
    floating_pnl: float = 0.0
    max_drawdown_demo_percent: float = 0.0
    margin: float | None = None
    free_margin: float | None = None
    daily_loss: float = 0.0
    stop_reason_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        uptime = 0.0
        if self.ended_at_utc is not None:
            uptime = max(
                0.0,
                (
                    datetime.fromisoformat(self.ended_at_utc)
                    - datetime.fromisoformat(self.started_at_utc)
                ).total_seconds(),
            )
        value.update(
            {
                "uptime_seconds": uptime,
                "fresh_data_rate": (
                    self.fresh_data_cycles / self.cycles if self.cycles else 0.0
                ),
                "broker_submission_called": self.orders_submitted > 0,
                "safe_to_trade": False,
                "real_trading": False,
                "execution_allowed": False,
            }
        )
        return value


def evaluate_precanary_cycle(evidence: SoakCycleEvidence) -> SoakCycleDecision:
    """Evaluate one cycle and fail closed before any possible broker action."""
    reasons: list[str] = []
    if evidence.broker_submission_called:
        reasons.append("unexpected_broker_submission")
    if evidence.account_mode != "DEMO":
        reasons.append("account_identity_hard_block")
    if evidence.broker != EXPECTED_BROKER:
        reasons.append("broker_identity_hard_block")
    if evidence.server != EXPECTED_SERVER:
        reasons.append("server_identity_hard_block")
    if evidence.terminal_path.casefold() != EXPECTED_TERMINAL.casefold():
        reasons.append("terminal_identity_hard_block")
    if not evidence.terminal_connected:
        reasons.append("terminal_disconnected")
    if not evidence.terminal_trade_allowed:
        reasons.append("terminal_trade_not_allowed")
    if not evidence.account_trade_allowed:
        reasons.append("account_trade_not_allowed")
    if not evidence.account_trade_expert:
        reasons.append("account_expert_trade_not_allowed")
    if evidence.symbol != EXPECTED_SYMBOL:
        reasons.append("symbol_not_authorized")
    if evidence.trade_mode == 0:
        reasons.append("market_disabled")
    elif evidence.trade_mode != 4:
        reasons.append("symbol_trade_mode_not_full")
    if not evidence.data_fresh:
        reasons.append("stale_data")
    if not evidence.time_normalization_valid:
        reasons.append("market_time_normalization_invalid")
    if (
        evidence.spread_limit_price <= 0
        or evidence.spread_limit_points <= 0
        or evidence.spread_price < 0
        or evidence.spread_points < 0
    ):
        reasons.append("spread_evidence_invalid")
    else:
        implied_point = evidence.spread_limit_price / evidence.spread_limit_points
        calculated_points = evidence.spread_price / implied_point
        if abs(calculated_points - evidence.spread_points) > 0.01:
            reasons.append("spread_scale_mismatch")
    if (
        evidence.spread_price > evidence.spread_limit_price
        or evidence.spread_points > evidence.spread_limit_points
    ):
        reasons.append("excessive_spread")
    if evidence.reconciliation_status != "RECONCILED":
        reasons.append("reconciliation_mismatch")
    if evidence.kill_switch_engaged:
        reasons.append("kill_switch_engaged")
    if evidence.position_count > 1:
        reasons.append("position_limit_exceeded")
    if evidence.position_count and not evidence.position_reconciled:
        reasons.append("position_orphan")
    if evidence.pending_execution:
        reasons.append("unknown_execution_state")
    if evidence.proposal_duplicate:
        reasons.append("duplicate_execution_suspicion")
    if evidence.execution_error is not None:
        error = evidence.execution_error.upper()
        reasons.append(error if error in KNOWN_EXECUTION_ERRORS else "UNKNOWN_RESULT")
    risk_stops = _IMMEDIATE_RISK_STOPS.intersection(evidence.risk_reason_codes)
    reasons.extend(sorted(risk_stops))
    reasons = list(dict.fromkeys(reasons))
    if reasons:
        status = (
            "HARD_BLOCK"
            if _IDENTITY_HARD_BLOCKS.intersection(reasons)
            else "STOPPED_PRE_CANARY"
        )
        return SoakCycleDecision(
            status=status,
            reason_codes=tuple(reasons),
            action="SAFE_STOP",
            stop=True,
        )
    if evidence.position_count == 1:
        return SoakCycleDecision(
            status="POSITION_OPEN_MONITOR_ONLY",
            reason_codes=("existing_reconciled_position",),
            action="OBSERVE_AND_RECONCILE",
            stop=False,
        )
    if evidence.no_trade or not evidence.proposal_available:
        return SoakCycleDecision(
            status="NO_TRADE",
            reason_codes=("no_valid_setup",),
            action="WAIT",
            stop=False,
        )
    if evidence.risk_status != "ALLOW_DEMO":
        return SoakCycleDecision(
            status="RISK_BLOCK",
            reason_codes=evidence.risk_reason_codes or ("risk_not_approved",),
            action="WAIT",
            stop=False,
        )
    return SoakCycleDecision(
        status="STAGE0_READY",
        reason_codes=("order_check_required_before_canary",),
        action="RUN_STAGE0_ONCE",
        stop=True,
    )


def run_bounded_precanary_soak(
    *,
    observe: Callable[[int], SoakCycleEvidence],
    report_dir: str | Path,
    limits: SoakLimits | None = None,
    git_checkpoint: str = "UNCOMMITTED",
    clock: Callable[[], datetime] | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> dict[str, object]:
    """Run a manual bounded pre-CANARY loop; never call an execution API."""
    policy = limits or SoakLimits()
    now = clock or (lambda: datetime.now(UTC))
    wait = sleeper or time.sleep
    started = _aware_utc(now())
    metrics = SoakMetrics(started_at_utc=started.isoformat())
    repeated_failure: tuple[str, ...] | None = None
    repeated_count = 0
    last_evidence: SoakCycleEvidence | None = None
    last_decision: SoakCycleDecision | None = None

    for cycle_number in range(1, policy.max_cycles + 1):
        current = _aware_utc(now())
        if (current - started).total_seconds() >= policy.max_duration_seconds:
            metrics.status = "SOAK_WINDOW_COMPLETE_PRE_CANARY"
            metrics.ended_at_utc = current.isoformat()
            break
        try:
            evidence = observe(cycle_number)
            decision = evaluate_precanary_cycle(evidence)
        except Exception:  # fail closed without leaking exception content
            metrics.exceptions += 1
            decision = SoakCycleDecision(
                status="STOPPED_PRE_CANARY",
                reason_codes=("observation_exception",),
                action="SAFE_STOP",
                stop=True,
            )
            evidence = None

        metrics.cycles += 1
        if evidence is not None:
            last_evidence = evidence
            _update_metrics(metrics, evidence, decision)
        last_decision = decision

        signature = decision.reason_codes if decision.status == "RISK_BLOCK" else None
        if signature is not None and signature == repeated_failure:
            repeated_count += 1
        elif signature is not None:
            repeated_failure = signature
            repeated_count = 1
        else:
            repeated_failure = None
            repeated_count = 0
        if repeated_count >= policy.max_same_failure:
            decision = replace(
                decision,
                status="BLOCKED_RECURRING_FAILURE",
                reason_codes=("recurring_failure", *decision.reason_codes),
                action="SAFE_STOP",
                stop=True,
            )
            last_decision = decision

        metrics.status = decision.status
        metrics.stop_reason_codes = list(decision.reason_codes) if decision.stop else []
        metrics.ended_at_utc = _aware_utc(now()).isoformat()
        snapshot = _snapshot(
            metrics, last_evidence, last_decision, policy, git_checkpoint
        )
        write_live_soak_reports(report_dir=report_dir, snapshot=snapshot)
        if decision.stop:
            return snapshot
        wait(float(policy.cycle_interval_seconds))
    else:
        metrics.status = "SOAK_CYCLE_LIMIT_COMPLETE_PRE_CANARY"
        metrics.ended_at_utc = _aware_utc(now()).isoformat()

    snapshot = _snapshot(metrics, last_evidence, last_decision, policy, git_checkpoint)
    write_live_soak_reports(report_dir=report_dir, snapshot=snapshot)
    return snapshot


def write_live_soak_reports(*, report_dir: str | Path, snapshot: dict[str, object]) -> None:
    """Persist the four required sanitized RC1 reports."""
    destination = Path(report_dir)
    destination.mkdir(parents=True, exist_ok=True)
    metrics = _mapping(snapshot.get("metrics"))
    evidence = _mapping(snapshot.get("last_evidence"))
    decision = _mapping(snapshot.get("last_decision"))
    broker_submission_called = str(
        bool(snapshot.get("broker_submission_called", False))
    ).lower()
    guardrails = (
        f"broker_submission_called={broker_submission_called}\n"
        "safe_to_trade=false\n"
        "real_trading=false\n"
        "execution_allowed=false"
    )
    status = (
        "# ODIN DEMO LIVE SOAK RC1 — STATUS\n\n"
        f"Status: `{snapshot.get('status')}`\n\n"
        f"Cycles: `{metrics.get('cycles', 0)}`\n\n"
        f"Decision: `{decision.get('status', 'UNAVAILABLE')}`\n\n"
        f"Reason codes: `{decision.get('reason_codes', [])}`\n\n"
        f"```text\n{guardrails}\n```\n"
    )
    incidents = (
        "# ODIN DEMO LIVE SOAK RC1 — INCIDENTS\n\n"
        f"- observed_at_utc: `{evidence.get('observed_at_utc', 'UNAVAILABLE')}`\n"
        f"- status: `{decision.get('status', 'UNAVAILABLE')}`\n"
        f"- evidence: `{decision.get('reason_codes', [])}`\n"
        "- impact: broker execution remained disabled\n"
        "- root cause: see reason codes and preserved cycle evidence\n"
        "- fix: none unless separately validated as technical and reversible\n"
        "- tests: bounded controller validation required before checkpoint\n"
        f"- checkpoint: `{snapshot.get('git_checkpoint', 'UNCOMMITTED')}`\n\n"
        f"```text\n{guardrails}\n```\n"
    )
    repairs = (
        "# ODIN DEMO LIVE SOAK RC1 — SELF-REPAIRS\n\n"
        f"Self-repairs: `{metrics.get('self_repairs', 0)}`\n\n"
        f"Failed repairs: `{metrics.get('failed_repairs', 0)}`\n\n"
        "No risk limit, financial permission or guardrail may be repaired automatically.\n\n"
        f"```text\n{guardrails}\n```\n"
    )
    (destination / "ODIN_DEMO_LIVE_SOAK_STATUS.md").write_text(status, encoding="utf-8")
    (destination / "ODIN_DEMO_LIVE_SOAK_METRICS.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8"
    )
    (destination / "ODIN_DEMO_LIVE_SOAK_INCIDENTS.md").write_text(
        incidents, encoding="utf-8"
    )
    (destination / "ODIN_DEMO_LIVE_SOAK_SELF_REPAIRS.md").write_text(
        repairs, encoding="utf-8"
    )


def _update_metrics(
    metrics: SoakMetrics, evidence: SoakCycleEvidence, decision: SoakCycleDecision
) -> None:
    if evidence.data_fresh:
        metrics.fresh_data_cycles += 1
    if decision.status in {"HARD_BLOCK", "STOPPED_PRE_CANARY", "RISK_BLOCK"}:
        metrics.blocked_cycles += 1
    if decision.status == "NO_TRADE":
        metrics.no_trade_count += 1
    if evidence.proposal_available:
        metrics.trade_proposals += 1
    if evidence.risk_status != "ALLOW_DEMO":
        metrics.risk_block_count += 1
    if evidence.broker_submission_called:
        metrics.orders_submitted += 1
    if evidence.order_filled:
        metrics.orders_filled += 1
    if evidence.order_rejected:
        metrics.orders_rejected += 1
    if evidence.proposal_duplicate:
        metrics.duplicates_prevented += 1
    if evidence.reconciliation_status != "RECONCILED":
        metrics.reconciliation_errors += 1
    if not evidence.terminal_connected:
        metrics.mt5_disconnects += 1
    metrics.last_spread_price = evidence.spread_price
    metrics.last_spread_points = evidence.spread_points
    metrics.last_data_age_seconds = evidence.data_age_seconds
    metrics.reconnect_time_seconds = evidence.reconnect_time_seconds
    metrics.slippage_points = evidence.slippage_points
    metrics.execution_latency_ms = evidence.execution_latency_ms
    metrics.realized_pnl = evidence.realized_pnl
    metrics.floating_pnl = evidence.floating_pnl
    metrics.max_drawdown_demo_percent = max(
        metrics.max_drawdown_demo_percent, evidence.drawdown_demo_percent
    )
    metrics.margin = evidence.margin
    metrics.free_margin = evidence.free_margin
    metrics.daily_loss = evidence.daily_loss


def _snapshot(
    metrics: SoakMetrics,
    evidence: SoakCycleEvidence | None,
    decision: SoakCycleDecision | None,
    limits: SoakLimits,
    git_checkpoint: str,
) -> dict[str, object]:
    return {
        "schema": "odin.demo_live_soak/v1",
        "status": metrics.status,
        "mode": "PRE_CANARY_SUPERVISED_ONLY",
        "limits": asdict(limits),
        "metrics": metrics.to_dict(),
        "last_evidence": asdict(evidence) if evidence else None,
        "last_decision": asdict(decision) if decision else None,
        "git_checkpoint": git_checkpoint,
        "broker_submission_called": metrics.orders_submitted > 0,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock_must_be_timezone_aware")
    return value.astimezone(UTC)


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}
