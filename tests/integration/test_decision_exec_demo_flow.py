from datetime import timedelta
from pathlib import Path

from core.runtime import CoreRuntimeController
from decision import DecisionCandidate, DecisionEngine
from exec import DemoExecutionEngine, PreExecutionContext
from market import MarketAssessment, MarketEvaluator, MarketSampleInput
from persistence.sqlite_state_store import SQLiteStateStore
from risk import RiskAssessment, RiskEvaluator, RiskInput
from shared.config import OdinSettings
from shared.contracts import DecisionInputSnapshot
from shared.enums import (
    DecisionOutput,
    ExecutionFinalResult,
    ExecutionState,
    GlobalState,
)
from shared.utils import utc_now


def write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "odin.local.toml"
    config_path.write_text(
        """
[core]
startup_timeout_ms = 15000
event_queue_max_size = 2048
heartbeat_timeout_ms = 500
heartbeat_grace_count = 1
allow_real_mode = false
recovery_required_on_unclean_shutdown = true
persist_on_critical_transition = true

[memory]
enabled = false
provider = "mempalace"
mode = "advisory"
freeze_into_decision_snapshot = true
freeze_into_learn_snapshot = true

[runtime]
state_dir = "__STATE_DIR__"
log_dir = "__LOG_DIR__"
backup_dir = "__BACKUP_DIR__"
memory_dir = "__MEMORY_DIR__"
""".replace("__STATE_DIR__", str(tmp_path / "state"))
        .replace("__LOG_DIR__", str(tmp_path / "logs"))
        .replace("__BACKUP_DIR__", str(tmp_path / "backups"))
        .replace("__MEMORY_DIR__", str(tmp_path / "memory")),
        encoding="utf-8",
    )
    return config_path


def ready_market_assessment() -> MarketAssessment:
    return MarketEvaluator().evaluate(
        MarketSampleInput(
            feed_available=True,
            market_open=True,
            sample_valid=True,
            sample_age_ms=100,
            latency_ms=20,
            spread_bps=1.0,
        )
    )


def allow_risk_assessment(market_assessment: MarketAssessment) -> RiskAssessment:
    return RiskEvaluator().evaluate(
        RiskInput(
            market=market_assessment,
            current_daily_pnl=0.0,
            max_daily_loss=500.0,
        )
    )


def promote_runtime_to_ready(runtime: CoreRuntimeController, market_assessment: MarketAssessment) -> None:
    runtime.process_event(market_assessment.to_core_event())
    runtime.process_event(market_assessment.to_core_event())


def build_decision_snapshot(
    runtime: CoreRuntimeController,
    market_assessment: MarketAssessment,
    risk_assessment: RiskAssessment,
) -> DecisionInputSnapshot:
    view = runtime.get_public_view()
    return DecisionInputSnapshot(
        global_state=view.state_code,
        current_mode=view.mode_code,
        market_state=market_assessment.market_state.value,
        context_class=market_assessment.context_state.value,
        feed_integrity_state=market_assessment.feed_integrity_state.value,
        risk_state=risk_assessment.risk_decision.value,
        kill_active=view.kill_active,
        active_block_vector_summary={
            "active_block_count": view.active_block_vector.active_block_count,
            "dominant_block_reason": view.dominant_block_reason,
        },
        instrument_snapshot_ref="market-snapshot-1",
        decision_config_version="decision-v1",
    )


def test_demo_pipeline_decision_to_exec_to_core_reaches_active(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)
    market_assessment = ready_market_assessment()
    risk_assessment = allow_risk_assessment(market_assessment)

    runtime.start()
    promote_runtime_to_ready(runtime, market_assessment)
    snapshot = build_decision_snapshot(runtime, market_assessment, risk_assessment)
    evaluation = DecisionEngine().evaluate(
        snapshot,
        [
            DecisionCandidate(
                hypothesis_id="hyp-1",
                tactic_id="tactic-breakout",
                instrument_id="EURUSD",
                side="BUY",
                score_value=0.91,
                min_score_threshold=0.8,
                reason_summary="breakout selected",
                price_reference=1.1000,
            )
        ],
        ttl_ms=3000,
        max_slippage=0.0002,
    )
    runtime.process_event(evaluation.result.to_core_event())
    assert evaluation.intent is not None

    report = DemoExecutionEngine().execute(
        evaluation.intent,
        PreExecutionContext(
            global_state=runtime.get_public_view().state_code,
            current_mode=runtime.get_public_view().mode_code,
            risk_decision=risk_assessment.risk_decision.value,
            market_state=market_assessment.market_state.value,
            market_readiness=market_assessment.readiness_state.value,
            current_executable_price=1.10005,
        ),
    )
    active_view = runtime.process_event(report.to_core_event())

    assert evaluation.result.decision_output == DecisionOutput.CANDIDATE_SELECTED
    assert report.snapshot.exec_state == ExecutionState.EXECUTION_CONFIRMED
    assert report.snapshot.final_result == ExecutionFinalResult.CONFIRMED_EXECUTED
    assert active_view.state_code == GlobalState.ACTIVE


def test_expired_intent_never_executes(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)
    market_assessment = ready_market_assessment()
    risk_assessment = allow_risk_assessment(market_assessment)

    runtime.start()
    promote_runtime_to_ready(runtime, market_assessment)
    snapshot = build_decision_snapshot(runtime, market_assessment, risk_assessment)
    issued_at = utc_now() - timedelta(seconds=5)
    evaluation = DecisionEngine().evaluate(
        snapshot,
        [
            DecisionCandidate(
                hypothesis_id="hyp-1",
                tactic_id="tactic-breakout",
                instrument_id="EURUSD",
                side="BUY",
                score_value=0.91,
                min_score_threshold=0.8,
                reason_summary="breakout selected",
                price_reference=1.1000,
            )
        ],
        ttl_ms=1000,
        max_slippage=0.0002,
        now_utc=issued_at,
    )
    assert evaluation.intent is not None

    report = DemoExecutionEngine().execute(
        evaluation.intent,
        PreExecutionContext(
            global_state=runtime.get_public_view().state_code,
            current_mode=runtime.get_public_view().mode_code,
            risk_decision=risk_assessment.risk_decision.value,
            market_state=market_assessment.market_state.value,
            market_readiness=market_assessment.readiness_state.value,
            current_executable_price=1.10005,
            now_utc=utc_now(),
        ),
    )
    view = runtime.process_event(report.to_core_event())

    assert report.core_event_type == "EV-INTENTION-EXPIRED"
    assert report.snapshot.exec_state == ExecutionState.CANCELLED_EXPIRED
    assert view.state_code == GlobalState.READY


def test_pre_submission_slippage_rejects_demo_execution(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)
    market_assessment = ready_market_assessment()
    risk_assessment = allow_risk_assessment(market_assessment)

    runtime.start()
    promote_runtime_to_ready(runtime, market_assessment)
    snapshot = build_decision_snapshot(runtime, market_assessment, risk_assessment)
    evaluation = DecisionEngine().evaluate(
        snapshot,
        [
            DecisionCandidate(
                hypothesis_id="hyp-1",
                tactic_id="tactic-breakout",
                instrument_id="EURUSD",
                side="BUY",
                score_value=0.91,
                min_score_threshold=0.8,
                reason_summary="breakout selected",
                price_reference=1.1000,
            )
        ],
        ttl_ms=3000,
        max_slippage=0.0002,
    )
    assert evaluation.intent is not None

    report = DemoExecutionEngine().execute(
        evaluation.intent,
        PreExecutionContext(
            global_state=runtime.get_public_view().state_code,
            current_mode=runtime.get_public_view().mode_code,
            risk_decision=risk_assessment.risk_decision.value,
            market_state=market_assessment.market_state.value,
            market_readiness=market_assessment.readiness_state.value,
            current_executable_price=1.1005,
        ),
    )
    view = runtime.process_event(report.to_core_event())

    assert report.core_event_type == "EV-EXEC-REJECTED-SLIPPAGE"
    assert report.snapshot.exec_state == ExecutionState.REJECTED
    assert report.snapshot.final_result == ExecutionFinalResult.CONFIRMED_REJECTED
    assert view.state_code == GlobalState.READY


def test_post_submission_divergence_blocks_core(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)
    market_assessment = ready_market_assessment()
    risk_assessment = allow_risk_assessment(market_assessment)

    runtime.start()
    promote_runtime_to_ready(runtime, market_assessment)
    snapshot = build_decision_snapshot(runtime, market_assessment, risk_assessment)
    evaluation = DecisionEngine().evaluate(
        snapshot,
        [
            DecisionCandidate(
                hypothesis_id="hyp-1",
                tactic_id="tactic-breakout",
                instrument_id="EURUSD",
                side="BUY",
                score_value=0.91,
                min_score_threshold=0.8,
                reason_summary="breakout selected",
                price_reference=1.1000,
            )
        ],
        ttl_ms=3000,
        max_slippage=0.0002,
    )
    assert evaluation.intent is not None

    report = DemoExecutionEngine().execute(
        evaluation.intent,
        PreExecutionContext(
            global_state=runtime.get_public_view().state_code,
            current_mode=runtime.get_public_view().mode_code,
            risk_decision=risk_assessment.risk_decision.value,
            market_state=market_assessment.market_state.value,
            market_readiness=market_assessment.readiness_state.value,
            current_executable_price=1.10005,
            confirmed_price=1.1005,
        ),
    )
    view = runtime.process_event(report.to_core_event())

    assert report.core_event_type == "EV-EXEC-DIVERGENCE"
    assert report.snapshot.exec_state == ExecutionState.DIVERGENT
    assert report.snapshot.final_result == ExecutionFinalResult.CRITICAL_DIVERGENCE
    assert view.state_code == GlobalState.BLOCKED_FAULT


def test_expired_intent_persists_reason_code_in_execution_ledger(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    runtime = CoreRuntimeController(settings, state_store=store)
    market_assessment = ready_market_assessment()
    risk_assessment = allow_risk_assessment(market_assessment)

    runtime.start()
    promote_runtime_to_ready(runtime, market_assessment)
    snapshot = build_decision_snapshot(runtime, market_assessment, risk_assessment)
    evaluation = DecisionEngine().evaluate(
        snapshot,
        [
            DecisionCandidate(
                hypothesis_id="hyp-exp",
                tactic_id="tactic-exp",
                instrument_id="EURUSD",
                side="BUY",
                score_value=0.91,
                min_score_threshold=0.8,
                reason_summary="expiry path",
                price_reference=1.1000,
            )
        ],
        ttl_ms=1000,
        max_slippage=0.0002,
        now_utc=utc_now() - timedelta(seconds=5),
    )
    assert evaluation.intent is not None

    report = DemoExecutionEngine(ledger_store=store).execute(
        evaluation.intent,
        PreExecutionContext(
            global_state=runtime.get_public_view().state_code,
            current_mode=runtime.get_public_view().mode_code,
            risk_decision=risk_assessment.risk_decision.value,
            market_state=market_assessment.market_state.value,
            market_readiness=market_assessment.readiness_state.value,
            current_executable_price=1.10005,
            now_utc=utc_now(),
        ),
    )

    assert report.core_event_type == "EV-INTENTION-EXPIRED"
    latest = store.read_latest_execution_ledger_record()
    assert latest is not None
    assert latest.intent_id == evaluation.intent.intent_id
    assert latest.reason_summary == "intent_expired"
    assert latest.exec_state == ExecutionState.CANCELLED_EXPIRED


def test_exec_divergence_reason_and_idempotency_are_persisted(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    runtime = CoreRuntimeController(settings, state_store=store)
    market_assessment = ready_market_assessment()
    risk_assessment = allow_risk_assessment(market_assessment)

    runtime.start()
    promote_runtime_to_ready(runtime, market_assessment)
    snapshot = build_decision_snapshot(runtime, market_assessment, risk_assessment)
    evaluation = DecisionEngine().evaluate(
        snapshot,
        [
            DecisionCandidate(
                hypothesis_id="hyp-div",
                tactic_id="tactic-div",
                instrument_id="EURUSD",
                side="BUY",
                score_value=0.91,
                min_score_threshold=0.8,
                reason_summary="divergence path",
                price_reference=1.1000,
            )
        ],
        ttl_ms=3000,
        max_slippage=0.0002,
    )
    assert evaluation.intent is not None
    engine = DemoExecutionEngine(ledger_store=store)
    context = PreExecutionContext(
        global_state=runtime.get_public_view().state_code,
        current_mode=runtime.get_public_view().mode_code,
        risk_decision=risk_assessment.risk_decision.value,
        market_state=market_assessment.market_state.value,
        market_readiness=market_assessment.readiness_state.value,
        current_executable_price=1.10005,
        confirmed_price=1.1005,
    )

    first = engine.execute(evaluation.intent, context)
    first_view = runtime.process_event(first.to_core_event())
    second = engine.execute(evaluation.intent, context)

    assert first.snapshot.exec_state == ExecutionState.DIVERGENT
    assert first.snapshot.reason_summary == "slippage_divergence_post_submission"
    assert first_view.state_code == GlobalState.BLOCKED_FAULT
    assert first_view.dominant_block_reason == "slippage_divergence_post_submission"
    assert second.was_deduplicated is True
    assert second.snapshot.exec_state == first.snapshot.exec_state

    records = store.list_execution_ledger_records(intent_id=evaluation.intent.intent_id)
    assert len(records) == 2
    assert sorted(record.was_deduplicated for record in records) == [False, True]
    assert all(record.reason_summary == "slippage_divergence_post_submission" for record in records)
