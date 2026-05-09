from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from shared.enums import AssetClass
from shared.utils import ensure_utc, utc_now


@dataclass(frozen=True, slots=True)
class ExternalQuote:
    symbol: str
    provider: str
    timestamp_utc: datetime
    bid: float | None = None
    ask: float | None = None
    last_price: float | None = None
    currency: str | None = None
    from_cache: bool = False
    warning: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp_utc", ensure_utc(self.timestamp_utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "provider": self.provider,
            "timestamp_utc": self.timestamp_utc.isoformat(),
            "bid": self.bid,
            "ask": self.ask,
            "last_price": self.last_price,
            "currency": self.currency,
            "from_cache": self.from_cache,
            "warning": self.warning,
        }


@dataclass(frozen=True, slots=True)
class EconomicEvent:
    event_id: str
    provider: str
    title: str
    country: str
    event_time_utc: datetime
    impact: str = "medium"
    actual: str | None = None
    forecast: str | None = None
    previous: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_time_utc", ensure_utc(self.event_time_utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "provider": self.provider,
            "title": self.title,
            "country": self.country,
            "event_time_utc": self.event_time_utc.isoformat(),
            "impact": self.impact,
            "actual": self.actual,
            "forecast": self.forecast,
            "previous": self.previous,
        }


@dataclass(frozen=True, slots=True)
class AssetMetadata:
    symbol: str
    provider: str
    name: str
    asset_class: AssetClass
    currency: str | None = None
    exchange: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "provider": self.provider,
            "name": self.name,
            "asset_class": self.asset_class.value,
            "currency": self.currency,
            "exchange": self.exchange,
        }


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    provider: str
    enabled: bool
    configured: bool
    healthy: bool
    source_type: str
    last_error: str | None = None
    last_success_utc: datetime | None = None
    last_attempt_utc: datetime | None = None
    rate_limit_per_minute: int = 0
    rate_limited: bool = False

    def __post_init__(self) -> None:
        if self.last_success_utc is not None:
            object.__setattr__(self, "last_success_utc", ensure_utc(self.last_success_utc))
        if self.last_attempt_utc is not None:
            object.__setattr__(self, "last_attempt_utc", ensure_utc(self.last_attempt_utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "configured": self.configured,
            "healthy": self.healthy,
            "source_type": self.source_type,
            "last_error": self.last_error,
            "last_success_utc": self.last_success_utc.isoformat() if self.last_success_utc else None,
            "last_attempt_utc": self.last_attempt_utc.isoformat() if self.last_attempt_utc else None,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "rate_limited": self.rate_limited,
        }


@dataclass(frozen=True, slots=True)
class ExternalDataAuditRecord:
    operation: str
    provider: str
    success: bool
    detail: str
    recorded_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "recorded_at_utc", ensure_utc(self.recorded_at_utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "provider": self.provider,
            "success": self.success,
            "detail": self.detail,
            "recorded_at_utc": self.recorded_at_utc.isoformat(),
        }
