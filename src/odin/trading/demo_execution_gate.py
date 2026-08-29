"""Fail-closed gate between approved DEMO risk and the isolated MT5 adapter."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib

from odin.contracts.demo_execution import (
    CanaryAuthorization,
    DemoAccountEvidence,
    DemoAutomationAuthorization,
    DemoRiskLimits,
    TradeProposal,
)


def account_fingerprint(evidence: DemoAccountEvidence) -> str:
    identity = "|".join(
        (
            evidence.terminal_path,
            evidence.broker,
            evidence.server,
            evidence.login,
            evidence.broker_symbol,
        )
    )
    return hashlib.sha256(identity.encode()).hexdigest()


def evaluate_demo_execution_gate(
    proposal: TradeProposal,
    evidence: DemoAccountEvidence,
    risk_result: dict[str, object],
    *,
    duplicate_detected: bool,
    limits: DemoRiskLimits | None = None,
    canary_authorization: CanaryAuthorization | None = None,
    automation_authorization: DemoAutomationAuthorization | None = None,
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Authorize dry-run, one CANARY, or tightly scoped RC2 DEMO execution."""
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    policy = limits or DemoRiskLimits()
    hard_blocks = _identity_blocks(evidence)
    reasons = hard_blocks + _operational_blocks(
        proposal=proposal,
        evidence=evidence,
        risk_result=risk_result,
        duplicate_detected=duplicate_detected,
        limits=policy,
        now=now,
    )
    if reasons:
        return _blocked("HARD_BLOCK" if hard_blocks else "BLOCK", reasons)
    if canary_authorization is not None and automation_authorization is not None:
        return _blocked("BLOCK", ["conflicting_demo_authorizations"])
    if automation_authorization is not None:
        authorization_reasons = _automation_authorization_blocks(
            authorization=automation_authorization,
            proposal=proposal,
            evidence=evidence,
            limits=policy,
            now=now,
        )
        if authorization_reasons:
            return _blocked("BLOCK", authorization_reasons)
        return {
            "status": "AUTONOMOUS_DEMO_READY",
            "reason_codes": [],
            "order_check_allowed": True,
            "order_send_allowed": True,
            "demo_execution_enabled": True,
            "account_is_demo": True,
            "risk_approved": True,
            "reconciliation_ok": True,
            "account_fingerprint": account_fingerprint(evidence),
            "authorization_id": automation_authorization.authorization_id,
            "execution_allowed_scope": "ODIN_AUTONOMOUS_DEMO_RC2",
            "execution_allowed": False,
            "safe_to_trade": False,
            "real_trading": False,
        }
    authorization_reasons = _authorization_blocks(
        authorization=canary_authorization,
        proposal=proposal,
        evidence=evidence,
        now=now,
    )
    if canary_authorization is None:
        return {
            "status": "DRY_RUN_READY",
            "reason_codes": ["human_canary_confirmation_required"],
            "order_check_allowed": True,
            "order_send_allowed": False,
            "demo_execution_enabled": False,
            "account_is_demo": True,
            "risk_approved": True,
            "reconciliation_ok": True,
            "account_fingerprint": account_fingerprint(evidence),
            "execution_allowed_scope": "DEMO_DRY_RUN",
            "execution_allowed": False,
            "safe_to_trade": False,
            "real_trading": False,
        }
    if authorization_reasons:
        return _blocked("BLOCK", authorization_reasons)
    return {
        "status": "CANARY_READY",
        "reason_codes": [],
        "order_check_allowed": True,
        "order_send_allowed": True,
        "demo_execution_enabled": True,
        "account_is_demo": True,
        "risk_approved": True,
        "reconciliation_ok": True,
        "account_fingerprint": account_fingerprint(evidence),
        "execution_allowed_scope": "DEMO_CANARY_ONE_SHOT",
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _identity_blocks(evidence: DemoAccountEvidence) -> list[str]:
    reasons: list[str] = []
    if evidence.account_mode != "DEMO":
        reasons.append("account_not_proven_demo")
    identity = (
        ("terminal", evidence.expected_terminal_path, evidence.terminal_path),
        ("broker", evidence.expected_broker, evidence.broker),
        ("server", evidence.expected_server, evidence.server),
        ("login", evidence.expected_login, evidence.login),
        (
            "broker_symbol",
            evidence.expected_broker_symbol,
            evidence.broker_symbol,
        ),
    )
    for name, expected, observed in identity:
        if not expected or not observed or expected != observed:
            reasons.append(f"{name}_identity_mismatch")
    if evidence.fallback_used:
        reasons.append("account_fallback_forbidden")
    return reasons


def _operational_blocks(
    *,
    proposal: TradeProposal,
    evidence: DemoAccountEvidence,
    risk_result: dict[str, object],
    duplicate_detected: bool,
    limits: DemoRiskLimits,
    now: datetime,
) -> list[str]:
    reasons: list[str] = []
    checks = (
        (not evidence.terminal_connected, "terminal_disconnected"),
        (not evidence.terminal_trade_allowed, "terminal_trading_not_allowed"),
        (not evidence.market_open, "market_closed"),
        (evidence.reconciliation_status != "RECONCILED", "reconciliation_not_ok"),
        (evidence.kill_switch_engaged, "kill_switch_engaged"),
        (risk_result.get("status") != "ALLOW_DEMO", "risk_not_allow_demo"),
        (risk_result.get("risk_approved") is not True, "risk_not_approved"),
        (duplicate_detected, "duplicate_proposal"),
        (proposal.symbol != "EURUSD" or evidence.symbol != "EURUSD", "symbol_not_authorized"),
        (proposal.side not in {"BUY", "SELL"}, "side_not_authorized"),
        (proposal.data_quality != "VALID", "proposal_bad_data"),
        (evidence.open_positions >= limits.max_simultaneous_positions, "position_limit_reached"),
        (evidence.active_orders >= limits.max_simultaneous_orders, "order_limit_reached"),
        (evidence.free_margin < limits.minimum_free_margin, "minimum_free_margin_not_met"),
        (
            evidence.completed_trades_today >= limits.max_completed_trades_per_day,
            "daily_completed_trade_limit",
        ),
    )
    reasons.extend(reason for failed, reason in checks if failed)
    if evidence.market_time_status == "BLOCKED":
        reasons.extend(evidence.market_time_reason_codes or ("future_market_timestamp",))
    elif proposal.freshness != "FRESH" or not evidence.data_fresh:
        reasons.append("stale_data")
    if evidence.data_age_seconds < -limits.allowed_future_clock_skew_seconds:
        reasons.extend(("future_market_timestamp", "clock_skew_detected"))
    elif evidence.data_age_seconds > limits.stale_data_threshold_seconds:
        reasons.append("stale_data_threshold_exceeded")
    try:
        expiry = datetime.fromisoformat(proposal.expiry.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        reasons.append("proposal_expiry_invalid")
    else:
        if expiry <= now:
            reasons.append("proposal_expired")
    reasons.extend(_volume_and_stops_blocks(proposal, evidence, limits))
    return list(dict.fromkeys(reasons))


def _volume_and_stops_blocks(
    proposal: TradeProposal, evidence: DemoAccountEvidence, limits: DemoRiskLimits
) -> list[str]:
    reasons: list[str] = []
    if evidence.volume_step <= 0 or evidence.volume_min <= 0 or evidence.volume_max <= 0:
        reasons.append("symbol_volume_spec_invalid")
    else:
        steps = round((proposal.volume - evidence.volume_min) / evidence.volume_step)
        aligned = abs(evidence.volume_min + steps * evidence.volume_step - proposal.volume) < 1e-9
        if (
            proposal.volume < evidence.volume_min
            or proposal.volume > evidence.volume_max
            or proposal.volume > limits.max_position_size
            or not aligned
        ):
            reasons.append("invalid_volume")
    if any(value <= 0 for value in (proposal.entry_reference, proposal.stop_loss, proposal.take_profit)):
        reasons.append("invalid_price")
        return reasons
    minimum_distance = evidence.stops_level_points * evidence.point
    if proposal.side == "BUY":
        direction_valid = proposal.stop_loss < proposal.entry_reference < proposal.take_profit
    else:
        direction_valid = proposal.take_profit < proposal.entry_reference < proposal.stop_loss
    if not direction_valid:
        reasons.append("invalid_stop_direction")
    if (
        abs(proposal.entry_reference - proposal.stop_loss) < minimum_distance
        or abs(proposal.take_profit - proposal.entry_reference) < minimum_distance
    ):
        reasons.append("invalid_stop_distance")
    return reasons


def _authorization_blocks(
    *,
    authorization: CanaryAuthorization | None,
    proposal: TradeProposal,
    evidence: DemoAccountEvidence,
    now: datetime,
) -> list[str]:
    if authorization is None:
        return ["human_canary_confirmation_required"]
    reasons: list[str] = []
    if authorization.proposal_id != proposal.proposal_id:
        reasons.append("canary_proposal_mismatch")
    if authorization.account_fingerprint != account_fingerprint(evidence):
        reasons.append("canary_account_mismatch")
    if not authorization.single_use or authorization.consumed:
        reasons.append("canary_not_available_one_shot")
    try:
        issued = datetime.fromisoformat(authorization.issued_at_utc.replace("Z", "+00:00")).astimezone(UTC)
        expires = datetime.fromisoformat(authorization.expires_at_utc.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        reasons.append("canary_timestamp_invalid")
    else:
        if issued > now or expires <= now:
            reasons.append("canary_expired_or_not_yet_valid")
    return reasons


def _automation_authorization_blocks(
    *,
    authorization: DemoAutomationAuthorization,
    proposal: TradeProposal,
    evidence: DemoAccountEvidence,
    limits: DemoRiskLimits,
    now: datetime,
) -> list[str]:
    reasons: list[str] = []
    if authorization.scope != "ODIN_AUTONOMOUS_DEMO_RC2":
        reasons.append("automation_scope_invalid")
    if not authorization.enabled:
        reasons.append("automation_authorization_disabled")
    if authorization.account_fingerprint != account_fingerprint(evidence):
        reasons.append("automation_account_mismatch")
    if authorization.strategy_id != proposal.strategy_id:
        reasons.append("automation_strategy_mismatch")
    if not authorization.authorization_id:
        reasons.append("automation_authorization_id_missing")
    try:
        issued = datetime.fromisoformat(
            authorization.issued_at_utc.replace("Z", "+00:00")
        ).astimezone(UTC)
    except ValueError:
        reasons.append("automation_timestamp_invalid")
    else:
        if issued > now:
            reasons.append("automation_not_yet_valid")
    if (
        authorization.max_position_size <= 0
        or authorization.max_position_size > limits.max_position_size
        or authorization.max_position_size > 0.01
    ):
        reasons.append("automation_position_limit_invalid")
    if (
        authorization.max_completed_trades_per_day <= 0
        or authorization.max_completed_trades_per_day
        > limits.max_completed_trades_per_day
        or authorization.max_completed_trades_per_day > 3
    ):
        reasons.append("automation_trade_count_limit_invalid")
    if (
        authorization.max_daily_demo_loss <= 0
        or authorization.max_daily_demo_loss > limits.max_daily_demo_loss
        or authorization.max_daily_demo_loss > 5.0
    ):
        reasons.append("automation_daily_loss_limit_invalid")
    return reasons


def _blocked(status: str, reasons: list[str]) -> dict[str, object]:
    return {
        "status": status,
        "reason_codes": reasons,
        "order_check_allowed": False,
        "order_send_allowed": False,
        "demo_execution_enabled": False,
        "account_is_demo": False,
        "risk_approved": False,
        "reconciliation_ok": False,
        "execution_allowed_scope": "NONE",
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }
