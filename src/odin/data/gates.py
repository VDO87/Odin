"""Blocking data quality gates for market snapshots."""

from __future__ import annotations

from odin.contracts.data_quality import DataQualityGateResult, DataQualityReport
from odin.contracts.market_data import MarketSnapshot

MOCK_SPREAD_LIMIT = 0.00050


def evaluate_snapshot(snapshot: MarketSnapshot) -> DataQualityReport:
    gates = [
        _gate("bid_present", snapshot.bid is not None, "bid is required", {"bid": snapshot.bid}),
        _gate("ask_present", snapshot.ask is not None, "ask is required", {"ask": snapshot.ask}),
        _gate("bid_positive", _positive(snapshot.bid), "bid must be positive", {"bid": snapshot.bid}),
        _gate("ask_positive", _positive(snapshot.ask), "ask must be positive", {"ask": snapshot.ask}),
        _gate(
            "ask_greater_than_bid",
            _ask_greater_than_bid(snapshot),
            "ask must be greater than bid",
            {"bid": snapshot.bid, "ask": snapshot.ask},
        ),
        _gate(
            "spread_present",
            snapshot.spread is not None,
            "spread is required",
            {"spread": snapshot.spread},
        ),
        _gate(
            "spread_non_negative",
            snapshot.spread is not None and snapshot.spread >= 0,
            "spread must be non-negative",
            {"spread": snapshot.spread},
        ),
        _gate(
            "spread_within_mock_limit",
            snapshot.spread is not None and snapshot.spread <= MOCK_SPREAD_LIMIT,
            "spread exceeds mock limit",
            {"spread": snapshot.spread, "limit": MOCK_SPREAD_LIMIT},
        ),
        _gate(
            "timestamp_present",
            bool(snapshot.timestamp),
            "timestamp is required",
            {"timestamp": snapshot.timestamp},
        ),
        _gate(
            "source_present",
            bool(snapshot.source),
            "source is required",
            {"source": snapshot.source},
        ),
        _gate(
            "source_is_mock_for_a7",
            snapshot.source == "mock",
            "source must be mock for A7",
            {"source": snapshot.source},
        ),
    ]
    blocking_reasons = [gate.reason for gate in gates if not gate.passed and gate.blocking]
    warning_reasons = [gate.reason for gate in gates if not gate.passed and not gate.blocking]
    status = "INVALID" if blocking_reasons else "WARNING" if warning_reasons else "OK"
    return DataQualityReport(
        status=status,
        source=snapshot.source or "",
        symbol=snapshot.symbol,
        timestamp=snapshot.timestamp,
        safe_to_use_for_decision=False,
        gates=gates,
        blocking_reasons=blocking_reasons,
        warning_reasons=warning_reasons,
        read_only=True,
        execution_allowed=False,
        safe_to_trade=False,
        real_trading=False,
    )


def _gate(
    gate_name: str,
    passed: bool,
    reason: str,
    details: dict[str, object],
    *,
    blocking: bool = True,
) -> DataQualityGateResult:
    return DataQualityGateResult(
        status="OK" if passed else "INVALID" if blocking else "WARNING",
        gate_name=gate_name,
        passed=passed,
        reason="passed" if passed else reason,
        severity="INFO" if passed else "ERROR" if blocking else "WARNING",
        blocking=blocking,
        details=details,
    )


def _positive(value: float | None) -> bool:
    return value is not None and value > 0


def _ask_greater_than_bid(snapshot: MarketSnapshot) -> bool:
    return snapshot.bid is not None and snapshot.ask is not None and snapshot.ask > snapshot.bid

