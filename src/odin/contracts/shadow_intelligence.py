"""Provider-neutral, deterministic contracts for Shadow Intelligence only."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MarketBar:
    symbol: str
    timeframe: str
    timestamp_utc: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread: float | None
    source: str
    provenance: str
    quality_status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MarketState:
    symbol: str
    timeframe: str
    as_of_utc: str
    freshness: str
    data_quality: str
    trend: str
    volatility: float
    spread_proxy: float | None
    session: str
    availability: str
    source_reconciliation_status: str
    market_data_hash: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ContextPacket:
    source: str
    timestamp: str
    evidence: tuple[str, ...]
    confidence: float | None
    affected_assets: tuple[str, ...]
    time_horizon: str
    invalidators: tuple[str, ...]
    freshness: str
    provenance: str
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
