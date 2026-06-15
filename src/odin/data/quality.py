"""Market data quality checks."""

from __future__ import annotations

from odin.contracts.market_data import DataQuality, MarketSnapshot


def check_snapshot_quality(snapshot: MarketSnapshot) -> DataQuality:
    missing = []
    if snapshot.bid is None:
        missing.append("bid")
    if snapshot.ask is None:
        missing.append("ask")
    if snapshot.spread is None:
        missing.append("spread")
    if not snapshot.timestamp:
        missing.append("timestamp")
    if not snapshot.source:
        missing.append("source")

    spread_ok = snapshot.spread is not None and snapshot.spread >= 0
    timestamp_ok = bool(snapshot.timestamp)
    source_ok = snapshot.source == "mock"

    if missing:
        return DataQuality(
            status="INVALID",
            reason="missing required market data fields",
            missing_fields=missing,
            spread_ok=spread_ok,
            timestamp_ok=timestamp_ok,
            source_ok=source_ok,
        )
    if not spread_ok or not timestamp_ok or not source_ok:
        return DataQuality(
            status="WARNING",
            reason="market data quality check produced warnings",
            missing_fields=[],
            spread_ok=spread_ok,
            timestamp_ok=timestamp_ok,
            source_ok=source_ok,
        )
    return DataQuality(
        status="OK",
        reason="mock snapshot passed quality checks",
        missing_fields=[],
        spread_ok=True,
        timestamp_ok=True,
        source_ok=True,
    )

