from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, cast

from external_data.audit import ExternalDataAuditLog
from external_data.cache import TTLCache
from external_data.models import (
    AssetMetadata,
    EconomicEvent,
    ExternalDataAuditRecord,
    ExternalQuote,
    ProviderStatus,
)
from external_data.providers.alpha_vantage import AlphaVantageProvider
from external_data.providers.demo_provider import DemoProvider
from external_data.providers.trading_economics import TradingEconomicsProvider
from external_data.rate_limit import FixedWindowRateLimiter
from shared.config import OdinSettings
from shared.utils import utc_now


class QuoteProvider(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def fetch_quote(self, symbol: str) -> ExternalQuote: ...


class CalendarProvider(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def fetch_calendar(self) -> list[EconomicEvent]: ...


class AssetSearchProvider(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def search_assets(self, query: str) -> list[AssetMetadata]: ...


@dataclass(slots=True)
class _ProviderRuntime:
    provider: object
    source_type: str
    enabled: bool
    configured: bool
    healthy: bool = True
    last_error: str | None = None
    last_success_utc: datetime | None = None
    last_attempt_utc: datetime | None = None
    rate_limit_per_minute: int = 0
    rate_limited: bool = False

    @property
    def name(self) -> str:
        return str(getattr(self.provider, "name", self.provider.__class__.__name__))


class ExternalDataService:
    def __init__(self, settings: OdinSettings, *, audit_log: ExternalDataAuditLog) -> None:
        self._settings = settings
        self._cache = TTLCache()
        self._rate_limiter = FixedWindowRateLimiter()
        self._audit_log = audit_log

        demo_provider = DemoProvider()
        self._providers: dict[str, _ProviderRuntime] = {
            "demo": _ProviderRuntime(
                provider=demo_provider,
                source_type="demo",
                enabled=settings.external_data.demo_provider_enabled,
                configured=True,
                rate_limit_per_minute=0,
            ),
            "alpha_vantage": _ProviderRuntime(
                provider=AlphaVantageProvider(),
                source_type="external",
                enabled=settings.external_data.alpha_vantage_enabled,
                configured=False,
                rate_limit_per_minute=settings.external_data.alpha_vantage_rate_limit_per_minute,
            ),
            "trading_economics": _ProviderRuntime(
                provider=TradingEconomicsProvider(),
                source_type="external",
                enabled=settings.external_data.trading_economics_enabled,
                configured=False,
                rate_limit_per_minute=settings.external_data.trading_economics_rate_limit_per_minute,
            ),
        }
        self._refresh_provider_configured_flags()

    def get_status_payload(self) -> dict[str, Any]:
        self._refresh_provider_configured_flags()
        provider_statuses = [self._status_payload(runtime) for runtime in self._providers.values()]
        warnings: list[str] = []
        real_enabled = [
            runtime
            for key, runtime in self._providers.items()
            if key != "demo" and runtime.enabled
        ]
        if not real_enabled:
            warnings.append("real_provider_disabled_by_profile_or_config")
        elif not any(runtime.configured for runtime in real_enabled):
            warnings.append("real_provider_enabled_but_not_configured")

        return {
            "profile": self._settings.profile.name.value,
            "core_authority": False,
            "data_can_execute_orders": False,
            "providers": provider_statuses,
            "cache": self._cache.stats(),
            "warnings": warnings,
        }

    def get_quote_payload(self, symbol: str, *, force_refresh: bool = False) -> dict[str, Any]:
        normalized_symbol = symbol.strip().upper() or "EURUSD"
        cache_key = f"quote:{normalized_symbol}"
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if isinstance(cached, ExternalQuote):
                quote = ExternalQuote(
                    symbol=cached.symbol,
                    provider=cached.provider,
                    timestamp_utc=cached.timestamp_utc,
                    bid=cached.bid,
                    ask=cached.ask,
                    last_price=cached.last_price,
                    currency=cached.currency,
                    from_cache=True,
                    warning=cached.warning,
                )
                return {
                    "quote": quote.to_dict(),
                    "cache": self._cache.stats(),
                    "warnings": [],
                }

        warnings: list[str] = []
        quote = self._resolve_quote(normalized_symbol, warnings)
        self._cache.set(
            cache_key,
            quote,
            ttl_seconds=self._settings.external_data.quote_cache_ttl_seconds,
        )
        return {
            "quote": quote.to_dict(),
            "cache": self._cache.stats(),
            "warnings": warnings,
        }

    def get_calendar_payload(self) -> dict[str, Any]:
        cache_key = "calendar"
        cached = self._cache.get(cache_key)
        if isinstance(cached, list):
            events = [event.to_dict() for event in cached]
            return {
                "events": events,
                "next_event": events[0] if events else None,
                "cache": self._cache.stats(),
                "warnings": [],
            }

        warnings: list[str] = []
        events = self._resolve_calendar(warnings)
        events.sort(key=lambda item: item.event_time_utc)
        self._cache.set(
            cache_key,
            events,
            ttl_seconds=self._settings.external_data.calendar_cache_ttl_seconds,
        )
        payload_events = [event.to_dict() for event in events]
        return {
            "events": payload_events,
            "next_event": payload_events[0] if payload_events else None,
            "cache": self._cache.stats(),
            "warnings": warnings,
        }

    def search_assets_payload(self, query: str) -> dict[str, Any]:
        normalized_query = query.strip()
        cache_key = f"asset-search:{normalized_query.lower()}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, list):
            return {
                "query": normalized_query,
                "assets": [asset.to_dict() for asset in cached],
                "cache": self._cache.stats(),
                "warnings": [],
            }

        warnings: list[str] = []
        assets = self._resolve_assets(normalized_query, warnings)
        self._cache.set(
            cache_key,
            assets,
            ttl_seconds=self._settings.external_data.asset_search_cache_ttl_seconds,
        )
        return {
            "query": normalized_query,
            "assets": [asset.to_dict() for asset in assets],
            "cache": self._cache.stats(),
            "warnings": warnings,
        }

    def _resolve_quote(self, symbol: str, warnings: list[str]) -> ExternalQuote:
        for provider_key in ("alpha_vantage", "demo"):
            runtime = self._providers[provider_key]
            if not runtime.enabled:
                continue
            if not self._can_use_provider(runtime, operation="quote", warnings=warnings):
                continue
            provider = cast(QuoteProvider, runtime.provider)
            try:
                quote = provider.fetch_quote(symbol)
                self._mark_provider_success(runtime, operation="quote")
                return quote
            except Exception as error:  # pragma: no cover - defensive fallback path
                self._mark_provider_failure(runtime, operation="quote", error=error)
                warnings.append(f"{runtime.name}_quote_failed")
        demo = cast(QuoteProvider, self._providers["demo"].provider)
        return demo.fetch_quote(symbol)

    def _resolve_calendar(self, warnings: list[str]) -> list[EconomicEvent]:
        for provider_key in ("trading_economics", "demo"):
            runtime = self._providers[provider_key]
            if not runtime.enabled:
                continue
            if not self._can_use_provider(runtime, operation="calendar", warnings=warnings):
                continue
            provider = cast(CalendarProvider, runtime.provider)
            try:
                events = provider.fetch_calendar()
                self._mark_provider_success(runtime, operation="calendar")
                return events
            except Exception as error:  # pragma: no cover - defensive fallback path
                self._mark_provider_failure(runtime, operation="calendar", error=error)
                warnings.append(f"{runtime.name}_calendar_failed")
        demo = cast(CalendarProvider, self._providers["demo"].provider)
        return demo.fetch_calendar()

    def _resolve_assets(self, query: str, warnings: list[str]) -> list[AssetMetadata]:
        merged: dict[str, AssetMetadata] = {}
        for provider_key in ("alpha_vantage", "demo"):
            runtime = self._providers[provider_key]
            if not runtime.enabled:
                continue
            if not self._can_use_provider(runtime, operation="asset-search", warnings=warnings):
                continue
            provider = cast(AssetSearchProvider, runtime.provider)
            try:
                assets = provider.search_assets(query)
                self._mark_provider_success(runtime, operation="asset-search")
                for asset in assets:
                    merged[asset.symbol] = asset
            except Exception as error:  # pragma: no cover - defensive fallback path
                self._mark_provider_failure(runtime, operation="asset-search", error=error)
                warnings.append(f"{runtime.name}_asset_search_failed")
        return list(merged.values())

    def _can_use_provider(
        self,
        runtime: _ProviderRuntime,
        *,
        operation: str,
        warnings: list[str],
    ) -> bool:
        runtime.last_attempt_utc = utc_now()
        if runtime.source_type == "external":
            if not runtime.configured:
                runtime.healthy = False
                runtime.last_error = "provider_not_configured"
                warnings.append(f"{runtime.name}_not_configured")
                return False
            allowed = self._rate_limiter.allow(
                key=f"{runtime.name}:{operation}",
                max_calls=max(runtime.rate_limit_per_minute, 1),
                window_seconds=60,
            )
            runtime.rate_limited = not allowed
            if not allowed:
                runtime.last_error = "rate_limited"
                warnings.append(f"{runtime.name}_rate_limited")
                self._audit_log.append(
                    ExternalDataAuditRecord(
                        operation=operation,
                        provider=runtime.name,
                        success=False,
                        detail="rate_limited",
                    )
                )
                return False
        return True

    def _mark_provider_success(self, runtime: _ProviderRuntime, *, operation: str) -> None:
        runtime.healthy = True
        runtime.last_error = None
        runtime.last_success_utc = utc_now()
        runtime.rate_limited = False
        self._audit_log.append(
            ExternalDataAuditRecord(
                operation=operation,
                provider=runtime.name,
                success=True,
                detail="ok",
            )
        )

    def _mark_provider_failure(
        self,
        runtime: _ProviderRuntime,
        *,
        operation: str,
        error: Exception,
    ) -> None:
        runtime.healthy = False
        runtime.last_error = f"{error.__class__.__name__}:{error}"
        self._audit_log.append(
            ExternalDataAuditRecord(
                operation=operation,
                provider=runtime.name,
                success=False,
                detail=runtime.last_error,
            )
        )

    def _status_payload(self, runtime: _ProviderRuntime) -> dict[str, Any]:
        calls_in_window = 0
        if runtime.source_type == "external":
            calls_in_window = self._rate_limiter.calls_in_window(
                key=f"{runtime.name}:quote",
                window_seconds=60,
            )
        status = ProviderStatus(
            provider=runtime.name,
            enabled=runtime.enabled,
            configured=runtime.configured,
            healthy=runtime.healthy,
            source_type=runtime.source_type,
            last_error=runtime.last_error,
            last_success_utc=runtime.last_success_utc,
            last_attempt_utc=runtime.last_attempt_utc,
            rate_limit_per_minute=runtime.rate_limit_per_minute,
            rate_limited=runtime.rate_limited,
        ).to_dict()
        status["calls_in_window"] = calls_in_window
        return status

    def _refresh_provider_configured_flags(self) -> None:
        for runtime in self._providers.values():
            configured_fn = getattr(runtime.provider, "is_configured", None)
            runtime.configured = bool(configured_fn()) if callable(configured_fn) else False
