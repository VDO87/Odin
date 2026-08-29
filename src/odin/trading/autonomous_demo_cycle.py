"""Deterministic helpers for the bounded autonomous DEMO cycle.

This module has no broker submission capability.  It validates the immutable
RC2 policy, normalizes MT5 bars, invokes the existing Shadow strategy and
builds one bounded :class:`TradeProposal` for the execution service.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Iterable

from odin.contracts.demo_execution import (
    DemoAccountEvidence,
    DemoAutomationAuthorization,
    DemoRiskLimits,
    TradeProposal,
)
from odin.contracts.shadow_intelligence import MarketBar
from odin.decision.trade_proposal import build_trade_proposal
from odin.shadow.pipeline import shadow_decision
from odin.trading.demo_execution_gate import account_fingerprint
from odin.trading.market_time import normalize_broker_timestamp


@dataclass(frozen=True)
class AutonomousDemoPolicy:
    mode: str
    authorization_id: str
    authorized_at_utc: str
    required_canary_decision_id: str
    broker: str
    server: str
    terminal_path: str
    logical_symbol: str
    broker_symbol: str
    strategy_id: str
    fixed_volume: float
    max_simultaneous_positions: int
    max_simultaneous_orders: int
    max_completed_trades_per_day: int
    max_daily_demo_loss_eur: float
    max_risk_per_trade_eur: float
    max_drawdown_percent: float
    minimum_free_margin_eur: float
    max_spread: float
    stale_data_threshold_seconds: int
    allowed_future_clock_skew_seconds: int
    maximum_order_retries: int
    maximum_execution_slippage_points: int

    def limits(self) -> DemoRiskLimits:
        return DemoRiskLimits(
            max_risk_per_trade=self.max_risk_per_trade_eur,
            max_daily_demo_loss=self.max_daily_demo_loss_eur,
            max_drawdown_percent=self.max_drawdown_percent,
            max_position_size=self.fixed_volume,
            max_simultaneous_positions=self.max_simultaneous_positions,
            max_simultaneous_orders=self.max_simultaneous_orders,
            minimum_free_margin=self.minimum_free_margin_eur,
            max_spread=self.max_spread,
            stale_data_threshold_seconds=self.stale_data_threshold_seconds,
            allowed_future_clock_skew_seconds=self.allowed_future_clock_skew_seconds,
            maximum_order_retries=self.maximum_order_retries,
            maximum_execution_slippage_points=self.maximum_execution_slippage_points,
            max_completed_trades_per_day=self.max_completed_trades_per_day,
        )

    def authorization(self, evidence: DemoAccountEvidence) -> DemoAutomationAuthorization:
        return DemoAutomationAuthorization(
            authorization_id=self.authorization_id,
            account_fingerprint=account_fingerprint(evidence),
            issued_at_utc=self.authorized_at_utc,
            strategy_id=self.strategy_id,
            max_position_size=self.fixed_volume,
            max_completed_trades_per_day=self.max_completed_trades_per_day,
            max_daily_demo_loss=self.max_daily_demo_loss_eur,
        )


def load_autonomous_demo_policy(path: str | Path) -> AutonomousDemoPolicy:
    """Load the human-authorized policy and reject any widened/unsafe value."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("rc2_policy_unavailable_or_invalid") from error
    if not isinstance(value, dict):
        raise ValueError("rc2_policy_not_an_object")
    immutable = {
        "mode": "ODIN_AUTONOMOUS_DEMO_RC2",
        "authorization_scope": "LIMITED_DEMO_ONLY",
        "broker": "OANDA TMS Brokers S.A.",
        "server": "OANDATMS-MT5",
        "terminal_path": r"C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe",
        "logical_symbol": "EURUSD",
        "broker_symbol": "EURUSD.pro",
        "strategy_id": "trend_mean_v1",
        "fixed_volume": 0.01,
        "max_simultaneous_positions": 1,
        "max_simultaneous_orders": 1,
        "max_completed_trades_per_day": 3,
        "max_daily_demo_loss_eur": 5.0,
        "max_risk_per_trade_eur": 5.0,
        "fallback_allowed": False,
        "autonomous_demo_authorized": True,
        "kill_switch_engaged": False,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }
    mismatches = [key for key, expected in immutable.items() if value.get(key) != expected]
    excluded = value.get("excluded_terminal_paths")
    if excluded != [r"D:\ODIN_LOCAL\mt5\terminal64.exe"]:
        mismatches.append("excluded_terminal_paths")
    if mismatches:
        raise ValueError("rc2_policy_guardrail_mismatch:" + ",".join(sorted(mismatches)))
    for required in (
        "authorization_id",
        "authorized_at_utc",
        "required_canary_decision_id",
    ):
        if not isinstance(value.get(required), str) or not value[required]:
            raise ValueError(f"rc2_policy_{required}_missing")
    try:
        authorized = datetime.fromisoformat(str(value["authorized_at_utc"]).replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("rc2_policy_authorized_at_utc_invalid") from error
    if authorized.tzinfo is None or authorized.utcoffset() is None:
        raise ValueError("rc2_policy_authorized_at_utc_not_aware")
    numeric = {
        "max_drawdown_percent",
        "minimum_free_margin_eur",
        "max_spread",
        "stale_data_threshold_seconds",
        "allowed_future_clock_skew_seconds",
        "maximum_order_retries",
        "maximum_execution_slippage_points",
    }
    if any(not isinstance(value.get(key), (int, float)) for key in numeric):
        raise ValueError("rc2_policy_numeric_value_missing")
    return AutonomousDemoPolicy(
        mode=str(value["mode"]),
        authorization_id=str(value["authorization_id"]),
        authorized_at_utc=authorized.astimezone(UTC).isoformat(),
        required_canary_decision_id=str(value["required_canary_decision_id"]),
        broker=str(value["broker"]),
        server=str(value["server"]),
        terminal_path=str(value["terminal_path"]),
        logical_symbol=str(value["logical_symbol"]),
        broker_symbol=str(value["broker_symbol"]),
        strategy_id=str(value["strategy_id"]),
        fixed_volume=float(value["fixed_volume"]),
        max_simultaneous_positions=int(value["max_simultaneous_positions"]),
        max_simultaneous_orders=int(value["max_simultaneous_orders"]),
        max_completed_trades_per_day=int(value["max_completed_trades_per_day"]),
        max_daily_demo_loss_eur=float(value["max_daily_demo_loss_eur"]),
        max_risk_per_trade_eur=float(value["max_risk_per_trade_eur"]),
        max_drawdown_percent=float(value["max_drawdown_percent"]),
        minimum_free_margin_eur=float(value["minimum_free_margin_eur"]),
        max_spread=float(value["max_spread"]),
        stale_data_threshold_seconds=int(value["stale_data_threshold_seconds"]),
        allowed_future_clock_skew_seconds=int(value["allowed_future_clock_skew_seconds"]),
        maximum_order_retries=int(value["maximum_order_retries"]),
        maximum_execution_slippage_points=int(value["maximum_execution_slippage_points"]),
    )


def build_market_bars(
    rates: Iterable[dict[str, object]],
    *,
    broker: str,
    server: str,
    logical_symbol: str,
    point: float,
    now_utc: datetime,
) -> dict[str, object]:
    """Normalize provider M15 rates into the existing provider-neutral contract."""
    bars: list[MarketBar] = []
    previous_timestamp: datetime | None = None
    for rate in rates:
        normalized = normalize_broker_timestamp(
            rate.get("time"), now_utc=now_utc, broker=broker, server=server
        )
        if normalized.status == "BLOCKED" or normalized.normalized_event_time_utc is None:
            return _blocked("market_bar_time_normalization_blocked")
        timestamp = datetime.fromisoformat(normalized.normalized_event_time_utc)
        if previous_timestamp is not None and timestamp <= previous_timestamp:
            return _blocked("market_bars_not_strictly_increasing")
        previous_timestamp = timestamp
        try:
            open_price = _required_float(rate["open"])
            high = _required_float(rate["high"])
            low = _required_float(rate["low"])
            close = _required_float(rate["close"])
            volume = _required_float(rate.get("tick_volume", rate.get("real_volume", 0.0)))
            spread_points = _required_float(rate.get("spread", 0.0))
        except (KeyError, TypeError, ValueError):
            return _blocked("market_bar_numeric_value_invalid")
        if (
            min(open_price, high, low, close) <= 0
            or high < max(open_price, close)
            or low > min(open_price, close)
            or volume < 0
            or spread_points < 0
            or point <= 0
        ):
            return _blocked("market_bar_ohlc_invalid")
        bars.append(
            MarketBar(
                symbol=logical_symbol,
                timeframe="M15",
                timestamp_utc=normalized.normalized_event_time_utc,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                spread=spread_points * point,
                source="MetaTrader 5/OANDA TMS",
                provenance=f"{broker}|{server}|M15",
                quality_status="VALIDATED",
            )
        )
    if len(bars) < 5:
        return _blocked("insufficient_market_bars")
    return {
        "status": "VALIDATED",
        "bars": bars,
        "normalization_method": "SOURCE_PROFILE_CET_CEST_EU_V1",
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def build_trade_candidate(
    bars: list[MarketBar],
    *,
    tick: dict[str, object],
    symbol: dict[str, object],
    policy: AutonomousDemoPolicy,
    now_utc: datetime,
) -> dict[str, object]:
    """Build a deterministic decision and, only for BUY/SELL, one proposal."""
    decision = shadow_decision(
        bars,
        strategy_id=policy.strategy_id,
        now_utc=now_utc,
        kill_switch=False,
    )
    signal = decision.get("signal")
    if signal not in {"BUY", "SELL"}:
        return {
            "status": "NO_TRADE",
            "decision": decision,
            "proposal": None,
            "reason_codes": decision.get("reason_codes", ["decision_not_actionable"]),
            "execution_allowed": False,
            "safe_to_trade": False,
            "real_trading": False,
        }
    try:
        point = _required_float(symbol["point"])
        digits = _required_int(symbol["digits"])
        stops_level = _required_int(symbol.get("trade_stops_level", 0))
        entry = _required_float(tick["ask"] if signal == "BUY" else tick["bid"])
    except (KeyError, TypeError, ValueError):
        return _blocked("live_price_or_symbol_spec_invalid", decision=decision)
    if point <= 0 or entry <= 0:
        return _blocked("live_price_or_symbol_spec_invalid", decision=decision)
    distance = max(stops_level + 10, 100) * point
    if signal == "BUY":
        stop_loss = round(entry - distance, digits)
        take_profit = round(entry + distance * 2, digits)
    else:
        stop_loss = round(entry + distance, digits)
        take_profit = round(entry - distance * 2, digits)
    proposed = build_trade_proposal(
        decision,
        entry_reference=round(entry, digits),
        stop_loss=stop_loss,
        take_profit=take_profit,
        volume=policy.fixed_volume,
        now_utc=now_utc,
        lifetime_seconds=60,
    )
    proposal = proposed.get("proposal")
    if proposed.get("status") != "PROPOSED" or not isinstance(proposal, TradeProposal):
        return _blocked(
            "trade_proposal_blocked",
            decision=decision,
            reason_codes=proposed.get("reason_codes"),
        )
    return {
        "status": "PROPOSAL_CREATED",
        "decision": decision,
        "proposal": proposal,
        "reason_codes": [],
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def summarize_daily_deals(
    deals: Iterable[dict[str, object]] | None,
    *,
    broker_symbol: str,
    exit_entries: set[int],
) -> dict[str, object]:
    """Compute conservative realized P/L and completed positions for one UTC day."""
    if deals is None:
        return {
            "status": "BLOCKED",
            "reason_codes": ["daily_broker_history_unavailable"],
            "daily_realized_pnl": -5.0,
            "completed_trades_today": 3,
        }
    realized = 0.0
    completed_positions: set[int] = set()
    for deal in deals:
        if deal.get("symbol") != broker_symbol:
            continue
        try:
            realized += sum(
                _required_float(deal.get(key, 0.0) or 0.0)
                for key in ("profit", "commission", "swap", "fee")
            )
            entry = _required_int(deal.get("entry", -1))
            position_id = _required_int(deal.get("position_id", 0))
        except (TypeError, ValueError):
            return {
                "status": "BLOCKED",
                "reason_codes": ["daily_broker_history_invalid"],
                "daily_realized_pnl": -5.0,
                "completed_trades_today": 3,
            }
        if entry in exit_entries and position_id > 0:
            completed_positions.add(position_id)
    return {
        "status": "OK",
        "reason_codes": [],
        "daily_realized_pnl": round(realized, 2),
        "completed_trades_today": len(completed_positions),
    }


def _required_float(value: object) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError("numeric_value_required")
    return float(value)


def _required_int(value: object) -> int:
    if not isinstance(value, (int, float)):
        raise TypeError("integer_value_required")
    return int(value)


def _blocked(
    reason: str,
    *,
    decision: dict[str, object] | None = None,
    reason_codes: object | None = None,
) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "reason": reason,
        "reason_codes": reason_codes if isinstance(reason_codes, list) else [reason],
        "decision": decision,
        "proposal": None,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }
