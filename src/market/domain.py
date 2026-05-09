from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from shared.contracts import CoreEventEnvelope
from shared.enums import EventType, Severity
from shared.utils import ensure_utc, isoformat_utc, utc_now


class MarketState(StrEnum):
    VALID = "MS-10"
    DEGRADED = "MS-20"
    INVALID = "MS-30"
    CLOSED = "MS-40"
    UNAVAILABLE = "MS-50"


class ContextState(StrEnum):
    FAVORABLE = "MC-10"
    NEUTRAL = "MC-20"
    SENSITIVE = "MC-30"
    HOSTILE = "MC-40"
    INDETERMINATE = "MC-50"


class MarketReadiness(StrEnum):
    READY = "READY"
    READY_RESTRICTED = "READY_RESTRICTED"
    NOT_READY = "NOT_READY"
    UNAVAILABLE = "UNAVAILABLE"


class FeedIntegrityState(StrEnum):
    OK = "FI-10"
    DEGRADED = "FI-20"
    INVALID = "FI-30"
    UNAVAILABLE = "FI-40"


class SpreadState(StrEnum):
    NORMAL = "SP-10"
    WIDE = "SP-20"
    CRITICAL = "SP-30"
    UNKNOWN = "SP-40"


@dataclass(frozen=True, slots=True)
class MarketAssessment:
    market_state: MarketState
    context_state: ContextState
    readiness_state: MarketReadiness
    feed_integrity_state: FeedIntegrityState
    last_valid_update_utc: datetime
    instrument_scope: str | None = None
    spread_state: SpreadState = SpreadState.UNKNOWN
    news_guard_active: bool = False
    reason_code: str = "market_ready"
    reason_text: str | None = None
    observed_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "last_valid_update_utc", ensure_utc(self.last_valid_update_utc))
        object.__setattr__(self, "observed_at_utc", ensure_utc(self.observed_at_utc))
        if not self.reason_code:
            raise ValueError("reason_code is required")

    @property
    def event_type(self) -> str:
        if self.market_state == MarketState.CLOSED:
            return EventType.MARKET_CLOSED.value
        if self.market_state in {MarketState.INVALID, MarketState.UNAVAILABLE}:
            return EventType.MARKET_INVALID.value
        if self.context_state == ContextState.HOSTILE or self.spread_state == SpreadState.CRITICAL:
            return EventType.MARKET_HOSTILE.value
        if self.news_guard_active:
            return EventType.MARKET_NEWS_GUARD.value
        if self.market_state == MarketState.DEGRADED or self.readiness_state == MarketReadiness.READY_RESTRICTED:
            return EventType.MARKET_DEGRADED.value
        return EventType.MARKET_READY.value

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "market_state": self.market_state.value,
            "context_state": self.context_state.value,
            "context_class": self.context_state.value,
            "readiness_state": self.readiness_state.value,
            "feed_integrity_state": self.feed_integrity_state.value,
            "last_valid_update_utc": isoformat_utc(self.last_valid_update_utc),
            "instrument_scope": self.instrument_scope,
            "spread_state": self.spread_state.value,
            "news_guard_active": self.news_guard_active,
            "reason_code": self.reason_code,
        }
        if self.reason_text:
            payload["reason_text"] = self.reason_text
        return payload

    def to_core_event(self, source_module: str = "MARKET") -> CoreEventEnvelope:
        severity = {
            EventType.MARKET_READY.value: Severity.INFO,
            EventType.MARKET_DEGRADED.value: Severity.WARN,
            EventType.MARKET_NEWS_GUARD.value: Severity.WARN,
            EventType.MARKET_CLOSED.value: Severity.WARN,
            EventType.MARKET_HOSTILE.value: Severity.ERROR,
            EventType.MARKET_INVALID.value: Severity.ERROR,
        }[self.event_type]
        return CoreEventEnvelope(
            event_type=self.event_type,
            source_module=source_module,
            severity=severity,
            payload=self.to_payload(),
        )


@dataclass(frozen=True, slots=True)
class MarketSampleInput:
    feed_available: bool
    market_open: bool
    sample_valid: bool
    sample_age_ms: int
    latency_ms: int
    spread_bps: float | None = None
    news_guard_active: bool = False
    critical_context_missing: bool = False
    session_low_activity: bool = False
    instrument_scope: str | None = None
    observed_at_utc: datetime = field(default_factory=utc_now)
    max_valid_age_ms: int = 1_000
    max_degraded_age_ms: int = 3_000
    max_valid_latency_ms: int = 250
    max_degraded_latency_ms: int = 1_000
    max_normal_spread_bps: float = 2.5
    max_degraded_spread_bps: float = 6.0
    last_valid_update_utc: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at_utc", ensure_utc(self.observed_at_utc))
        if self.last_valid_update_utc is not None:
            object.__setattr__(self, "last_valid_update_utc", ensure_utc(self.last_valid_update_utc))
        if self.sample_age_ms < 0:
            raise ValueError("sample_age_ms must be >= 0")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")


@dataclass(frozen=True, slots=True)
class MarketOperationalInput:
    instrument_id: str
    feed_id: str
    feed_available: bool
    market_open: bool
    sample_valid: bool
    sample_age_ms: int
    latency_ms: int
    spread_bps: float | None = None
    news_guard_active: bool = False
    critical_context_missing: bool = False
    session_low_activity: bool = False
    heavy_enrichment_requested: bool = False
    observed_at_utc: datetime = field(default_factory=utc_now)
    last_valid_update_utc: datetime | None = None

    def __post_init__(self) -> None:
        if not self.instrument_id:
            raise ValueError("instrument_id is required")
        if not self.feed_id:
            raise ValueError("feed_id is required")
        object.__setattr__(self, "observed_at_utc", ensure_utc(self.observed_at_utc))
        if self.last_valid_update_utc is not None:
            object.__setattr__(self, "last_valid_update_utc", ensure_utc(self.last_valid_update_utc))
        if self.sample_age_ms < 0:
            raise ValueError("sample_age_ms must be >= 0")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")


@dataclass(frozen=True, slots=True)
class MarketRuntimeStatus:
    execution_profile: str
    market_profile: str
    instrument_scope: tuple[str, ...]
    feed_scope: tuple[str, ...]
    news_guard_enabled: bool
    spread_guard_enabled: bool
    heavy_enrichment_enabled: bool
    last_gate_status: str = "idle"
    last_rejection_reason: str | None = None
    last_instrument_id: str | None = None
    last_feed_id: str | None = None
    applied_restrictions: tuple[str, ...] = tuple()

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_profile": self.execution_profile,
            "market_profile": self.market_profile,
            "instrument_scope": list(self.instrument_scope),
            "feed_scope": list(self.feed_scope),
            "max_instruments": len(self.instrument_scope),
            "max_feeds": len(self.feed_scope),
            "news_guard_enabled": self.news_guard_enabled,
            "spread_guard_enabled": self.spread_guard_enabled,
            "heavy_enrichment_enabled": self.heavy_enrichment_enabled,
            "active_restrictions": list(self._active_restrictions()),
            "last_gate_status": self.last_gate_status,
            "last_rejection_reason": self.last_rejection_reason,
            "last_instrument_id": self.last_instrument_id,
            "last_feed_id": self.last_feed_id,
            "applied_restrictions": list(self.applied_restrictions),
        }

    def _active_restrictions(self) -> tuple[str, ...]:
        restrictions = [
            f"instrument_scope:{len(self.instrument_scope)}",
            f"feed_scope:{len(self.feed_scope)}",
        ]
        if not self.news_guard_enabled:
            restrictions.append("news_guard_disabled")
        if not self.spread_guard_enabled:
            restrictions.append("spread_guard_disabled")
        if not self.heavy_enrichment_enabled:
            restrictions.append("heavy_enrichment_disabled")
        return tuple(restrictions)


@dataclass(frozen=True, slots=True)
class MarketIngestionResult:
    assessment: MarketAssessment
    runtime_status: MarketRuntimeStatus
    effective_sample: MarketSampleInput | None = None


class MarketProfileGate:
    def __init__(self, settings: Any) -> None:
        profile_settings = getattr(settings, "profile", None)
        market_settings = getattr(settings, "market", settings)
        execution_profile = getattr(profile_settings, "name", "unknown")
        market_profile = getattr(market_settings, "profile", "unknown")
        self._base_status = MarketRuntimeStatus(
            execution_profile=getattr(execution_profile, "value", str(execution_profile)),
            market_profile=getattr(market_profile, "value", str(market_profile)),
            instrument_scope=tuple(getattr(market_settings, "instrument_scope", tuple())),
            feed_scope=tuple(getattr(market_settings, "feed_scope", tuple())),
            news_guard_enabled=bool(getattr(market_settings, "news_guard_enabled", True)),
            spread_guard_enabled=bool(getattr(market_settings, "spread_guard_enabled", True)),
            heavy_enrichment_enabled=bool(
                getattr(market_settings, "heavy_enrichment_enabled", True)
            ),
        )

    def current_status(self) -> MarketRuntimeStatus:
        return self._base_status

    def evaluate(self, sample: MarketOperationalInput) -> MarketRuntimeStatus:
        if self._base_status.instrument_scope and sample.instrument_id not in self._base_status.instrument_scope:
            return self._status_for_sample(
                sample,
                gate_status="rejected",
                rejection_reason="instrument_scope_rejected",
                applied_restrictions=("instrument_scope_rejected",),
            )
        if self._base_status.feed_scope and sample.feed_id not in self._base_status.feed_scope:
            return self._status_for_sample(
                sample,
                gate_status="rejected",
                rejection_reason="feed_scope_rejected",
                applied_restrictions=("feed_scope_rejected",),
            )

        applied_restrictions: list[str] = []
        if sample.news_guard_active and not self._base_status.news_guard_enabled:
            applied_restrictions.append("news_guard_forced_off")
        if sample.spread_bps is not None and not self._base_status.spread_guard_enabled:
            applied_restrictions.append("spread_guard_disabled")
        if sample.heavy_enrichment_requested and not self._base_status.heavy_enrichment_enabled:
            applied_restrictions.append("heavy_enrichment_dropped")

        return self._status_for_sample(
            sample,
            gate_status="accepted",
            applied_restrictions=tuple(applied_restrictions),
        )

    def _status_for_sample(
        self,
        sample: MarketOperationalInput,
        *,
        gate_status: str,
        rejection_reason: str | None = None,
        applied_restrictions: tuple[str, ...] = tuple(),
    ) -> MarketRuntimeStatus:
        return MarketRuntimeStatus(
            execution_profile=self._base_status.execution_profile,
            market_profile=self._base_status.market_profile,
            instrument_scope=self._base_status.instrument_scope,
            feed_scope=self._base_status.feed_scope,
            news_guard_enabled=self._base_status.news_guard_enabled,
            spread_guard_enabled=self._base_status.spread_guard_enabled,
            heavy_enrichment_enabled=self._base_status.heavy_enrichment_enabled,
            last_gate_status=gate_status,
            last_rejection_reason=rejection_reason,
            last_instrument_id=sample.instrument_id,
            last_feed_id=sample.feed_id,
            applied_restrictions=applied_restrictions,
        )


class MarketSampleAdapter:
    def __init__(self, settings: Any) -> None:
        self._market_settings = getattr(settings, "market", settings)

    def adapt(self, sample: MarketOperationalInput) -> MarketSampleInput:
        spread_bps = sample.spread_bps
        if not getattr(self._market_settings, "spread_guard_enabled", True):
            spread_bps = None
        news_guard_active = sample.news_guard_active and bool(
            getattr(self._market_settings, "news_guard_enabled", True)
        )
        return MarketSampleInput(
            feed_available=sample.feed_available,
            market_open=sample.market_open,
            sample_valid=sample.sample_valid,
            sample_age_ms=sample.sample_age_ms,
            latency_ms=sample.latency_ms,
            spread_bps=spread_bps,
            news_guard_active=news_guard_active,
            critical_context_missing=sample.critical_context_missing,
            session_low_activity=sample.session_low_activity,
            instrument_scope=sample.instrument_id,
            observed_at_utc=sample.observed_at_utc,
            max_valid_age_ms=int(getattr(self._market_settings, "max_valid_age_ms", 1_000)),
            max_degraded_age_ms=int(getattr(self._market_settings, "max_degraded_age_ms", 3_000)),
            max_valid_latency_ms=int(
                getattr(self._market_settings, "max_valid_latency_ms", 250)
            ),
            max_degraded_latency_ms=int(
                getattr(self._market_settings, "max_degraded_latency_ms", 1_000)
            ),
            max_normal_spread_bps=float(
                getattr(self._market_settings, "max_normal_spread_bps", 2.5)
            ),
            max_degraded_spread_bps=float(
                getattr(self._market_settings, "max_degraded_spread_bps", 6.0)
            ),
            last_valid_update_utc=sample.last_valid_update_utc,
        )


class MarketOperationalPipeline:
    def __init__(self, settings: Any) -> None:
        self._gate = MarketProfileGate(settings)
        self._adapter = MarketSampleAdapter(settings)
        self._evaluator = MarketEvaluator()

    def ingest(self, sample: MarketOperationalInput) -> MarketIngestionResult:
        runtime_status = self._gate.evaluate(sample)
        if runtime_status.last_gate_status == "rejected":
            return MarketIngestionResult(
                assessment=self._build_rejected_assessment(sample, runtime_status.last_rejection_reason),
                runtime_status=runtime_status,
            )
        effective_sample = self._adapter.adapt(sample)
        return MarketIngestionResult(
            assessment=self._evaluator.evaluate(effective_sample),
            runtime_status=runtime_status,
            effective_sample=effective_sample,
        )

    def current_status(self) -> MarketRuntimeStatus:
        return self._gate.current_status()

    @staticmethod
    def _build_rejected_assessment(
        sample: MarketOperationalInput,
        rejection_reason: str | None,
    ) -> MarketAssessment:
        return MarketAssessment(
            market_state=MarketState.INVALID,
            context_state=ContextState.INDETERMINATE,
            readiness_state=MarketReadiness.NOT_READY,
            feed_integrity_state=FeedIntegrityState.INVALID,
            last_valid_update_utc=sample.last_valid_update_utc or sample.observed_at_utc,
            instrument_scope=sample.instrument_id,
            spread_state=SpreadState.UNKNOWN,
            news_guard_active=False,
            reason_code=rejection_reason or "market_profile_rejected",
        )


class MarketEvaluator:
    def evaluate(self, sample: MarketSampleInput) -> MarketAssessment:
        last_valid_update = sample.last_valid_update_utc or sample.observed_at_utc
        spread_state = self._classify_spread(sample)

        if not sample.feed_available:
            return MarketAssessment(
                market_state=MarketState.UNAVAILABLE,
                context_state=ContextState.INDETERMINATE,
                readiness_state=MarketReadiness.UNAVAILABLE,
                feed_integrity_state=FeedIntegrityState.UNAVAILABLE,
                last_valid_update_utc=last_valid_update,
                instrument_scope=sample.instrument_scope,
                spread_state=SpreadState.UNKNOWN,
                news_guard_active=sample.news_guard_active,
                reason_code="feed_unavailable",
            )

        if not sample.market_open:
            return MarketAssessment(
                market_state=MarketState.CLOSED,
                context_state=ContextState.NEUTRAL,
                readiness_state=MarketReadiness.NOT_READY,
                feed_integrity_state=FeedIntegrityState.OK,
                last_valid_update_utc=last_valid_update,
                instrument_scope=sample.instrument_scope,
                spread_state=spread_state,
                news_guard_active=sample.news_guard_active,
                reason_code="market_closed",
            )

        if not sample.sample_valid or sample.critical_context_missing:
            return MarketAssessment(
                market_state=MarketState.INVALID,
                context_state=ContextState.INDETERMINATE,
                readiness_state=MarketReadiness.NOT_READY,
                feed_integrity_state=FeedIntegrityState.INVALID,
                last_valid_update_utc=last_valid_update,
                instrument_scope=sample.instrument_scope,
                spread_state=spread_state,
                news_guard_active=sample.news_guard_active,
                reason_code="sample_invalid",
            )

        if (
            sample.sample_age_ms > sample.max_degraded_age_ms
            or sample.latency_ms > sample.max_degraded_latency_ms
        ):
            return MarketAssessment(
                market_state=MarketState.INVALID,
                context_state=ContextState.INDETERMINATE,
                readiness_state=MarketReadiness.NOT_READY,
                feed_integrity_state=FeedIntegrityState.INVALID,
                last_valid_update_utc=last_valid_update,
                instrument_scope=sample.instrument_scope,
                spread_state=spread_state,
                news_guard_active=sample.news_guard_active,
                reason_code="feed_too_stale",
            )

        context_state = ContextState.FAVORABLE
        market_state = MarketState.VALID
        readiness_state = MarketReadiness.READY
        feed_integrity_state = FeedIntegrityState.OK
        reason_code = "market_ready"

        if spread_state == SpreadState.CRITICAL:
            context_state = ContextState.HOSTILE
            market_state = MarketState.DEGRADED
            readiness_state = MarketReadiness.NOT_READY
            feed_integrity_state = FeedIntegrityState.DEGRADED
            reason_code = "spread_critical"
        elif (
            sample.sample_age_ms > sample.max_valid_age_ms
            or sample.latency_ms > sample.max_valid_latency_ms
            or spread_state == SpreadState.WIDE
            or sample.session_low_activity
        ):
            context_state = ContextState.SENSITIVE
            market_state = MarketState.DEGRADED
            readiness_state = MarketReadiness.READY_RESTRICTED
            feed_integrity_state = FeedIntegrityState.DEGRADED
            reason_code = "market_degraded"
        else:
            context_state = ContextState.FAVORABLE if spread_state == SpreadState.NORMAL else ContextState.NEUTRAL

        if sample.news_guard_active:
            if readiness_state == MarketReadiness.READY:
                readiness_state = MarketReadiness.READY_RESTRICTED
            if context_state != ContextState.HOSTILE:
                context_state = ContextState.SENSITIVE
            if reason_code == "market_ready":
                reason_code = "news_guard_active"

        return MarketAssessment(
            market_state=market_state,
            context_state=context_state,
            readiness_state=readiness_state,
            feed_integrity_state=feed_integrity_state,
            last_valid_update_utc=last_valid_update,
            instrument_scope=sample.instrument_scope,
            spread_state=spread_state,
            news_guard_active=sample.news_guard_active,
            reason_code=reason_code,
        )

    def _classify_spread(self, sample: MarketSampleInput) -> SpreadState:
        if sample.spread_bps is None:
            return SpreadState.UNKNOWN
        if sample.spread_bps <= sample.max_normal_spread_bps:
            return SpreadState.NORMAL
        if sample.spread_bps <= sample.max_degraded_spread_bps:
            return SpreadState.WIDE
        return SpreadState.CRITICAL
