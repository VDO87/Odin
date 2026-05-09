from types import SimpleNamespace

from market import (
    ContextState,
    FeedIntegrityState,
    MarketAssessment,
    MarketEvaluator,
    MarketOperationalInput,
    MarketOperationalPipeline,
    MarketProfileGate,
    MarketReadiness,
    MarketSampleInput,
    MarketState,
    SpreadState,
)
from shared.utils import utc_now


def test_market_assessment_payload_contains_core_contract_fields() -> None:
    assessment = MarketAssessment(
        market_state=MarketState.VALID,
        context_state=ContextState.FAVORABLE,
        readiness_state=MarketReadiness.READY,
        feed_integrity_state=FeedIntegrityState.OK,
        last_valid_update_utc=utc_now(),
        instrument_scope="EURUSD",
        spread_state=SpreadState.NORMAL,
    )

    event = assessment.to_core_event()
    payload = event.payload

    assert event.event_type == "EV-MARKET-READY"
    assert payload["market_state"] == "MS-10"
    assert payload["context_state"] == "MC-10"
    assert payload["context_class"] == "MC-10"
    assert payload["readiness_state"] == "READY"
    assert payload["feed_integrity_state"] == "FI-10"
    assert payload["instrument_scope"] == "EURUSD"
    assert payload["spread_state"] == "SP-10"
    assert payload["news_guard_active"] is False
    assert "last_valid_update_utc" in payload


def test_market_evaluator_marks_wide_spread_as_degraded() -> None:
    assessment = MarketEvaluator().evaluate(
        MarketSampleInput(
            feed_available=True,
            market_open=True,
            sample_valid=True,
            sample_age_ms=100,
            latency_ms=20,
            spread_bps=4.0,
        )
    )

    assert assessment.market_state == MarketState.DEGRADED
    assert assessment.context_state == ContextState.SENSITIVE
    assert assessment.readiness_state == MarketReadiness.READY_RESTRICTED
    assert assessment.to_core_event().event_type == "EV-MARKET-DEGRADED"


def make_runtime_settings(
    *,
    execution_profile: str = "lite",
    market_profile: str = "simple",
    instrument_scope: tuple[str, ...] = ("EURUSD",),
    feed_scope: tuple[str, ...] = ("primary",),
    news_guard_enabled: bool = False,
    spread_guard_enabled: bool = True,
    heavy_enrichment_enabled: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        profile=SimpleNamespace(name=execution_profile),
        market=SimpleNamespace(
            profile=market_profile,
            instrument_scope=instrument_scope,
            feed_scope=feed_scope,
            news_guard_enabled=news_guard_enabled,
            spread_guard_enabled=spread_guard_enabled,
            heavy_enrichment_enabled=heavy_enrichment_enabled,
            max_valid_age_ms=1_000,
            max_degraded_age_ms=3_000,
            max_valid_latency_ms=250,
            max_degraded_latency_ms=1_000,
            max_normal_spread_bps=2.5,
            max_degraded_spread_bps=6.0,
        ),
    )


def test_market_profile_gate_rejects_instrument_outside_scope() -> None:
    gate = MarketProfileGate(make_runtime_settings())

    status = gate.evaluate(
        MarketOperationalInput(
            instrument_id="GBPUSD",
            feed_id="primary",
            feed_available=True,
            market_open=True,
            sample_valid=True,
            sample_age_ms=100,
            latency_ms=20,
        )
    )

    assert status.last_gate_status == "rejected"
    assert status.last_rejection_reason == "instrument_scope_rejected"
    assert status.last_instrument_id == "GBPUSD"
    assert status.last_feed_id == "primary"


def test_market_operational_pipeline_applies_profile_restrictions_before_evaluation() -> None:
    pipeline = MarketOperationalPipeline(
        make_runtime_settings(
            news_guard_enabled=False,
            spread_guard_enabled=False,
            heavy_enrichment_enabled=False,
        )
    )

    result = pipeline.ingest(
        MarketOperationalInput(
            instrument_id="EURUSD",
            feed_id="primary",
            feed_available=True,
            market_open=True,
            sample_valid=True,
            sample_age_ms=100,
            latency_ms=20,
            spread_bps=4.0,
            news_guard_active=True,
            heavy_enrichment_requested=True,
        )
    )

    assert result.runtime_status.last_gate_status == "accepted"
    assert result.effective_sample is not None
    assert result.effective_sample.news_guard_active is False
    assert result.effective_sample.spread_bps is None
    assert result.assessment.market_state == MarketState.VALID
    assert result.runtime_status.applied_restrictions == (
        "news_guard_forced_off",
        "spread_guard_disabled",
        "heavy_enrichment_dropped",
    )
