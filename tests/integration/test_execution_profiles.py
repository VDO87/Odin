from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import subprocess

from core.runtime import CoreRuntimeController
from dash import CoreDashBridge, DashboardControlActionRequest, DashboardPermissionContext
from exec import DemoExecutionEngine, PreExecutionContext
from market import MarketAssessment, MarketEvaluator, MarketOperationalInput, MarketSampleInput
from persistence.sqlite_state_store import SQLiteStateStore
from shared.config import OdinSettings
from shared.contracts import ExecutionIntent, GlobalStateSnapshot
from shared.enums import (
    DashboardSurface,
    ExecutionProfile,
    GlobalState,
    IntegrityClass,
    MarketProfile,
    OperationalMode,
    ReadinessClass,
)
from shared.utils import isoformat_utc


def write_config(
    tmp_path: Path,
    *,
    profile: str | None = "lite",
    memory_enabled: bool = False,
    instrument_scope: tuple[str, ...] = ("EURUSD", "GBPUSD"),
    feed_scope: tuple[str, ...] = ("primary", "backup"),
    news_guard_enabled: bool = True,
    spread_guard_enabled: bool = True,
    heavy_enrichment_enabled: bool = True,
) -> Path:
    profile_section = ""
    if profile is not None:
        profile_section = f'[profile]\nname = "{profile}"\n\n'
    instrument_scope_toml = ", ".join(f'"{instrument}"' for instrument in instrument_scope)
    feed_scope_toml = ", ".join(f'"{feed}"' for feed in feed_scope)
    config_path = tmp_path / "odin.local.toml"
    config_path.write_text(
        (
            profile_section
            + f"""
[core]
startup_timeout_ms = 15000
event_queue_max_size = 2048
heartbeat_timeout_ms = 500
heartbeat_grace_count = 1
allow_real_mode = false
recovery_required_on_unclean_shutdown = true
persist_on_critical_transition = true

[memory]
enabled = {"true" if memory_enabled else "false"}
provider = "mempalace"
mode = "advisory"
freeze_into_decision_snapshot = true
freeze_into_learn_snapshot = true

[market]
instrument_scope = [{instrument_scope_toml}]
feed_scope = [{feed_scope_toml}]
news_guard_enabled = {"true" if news_guard_enabled else "false"}
spread_guard_enabled = {"true" if spread_guard_enabled else "false"}
heavy_enrichment_enabled = {"true" if heavy_enrichment_enabled else "false"}

[runtime]
state_dir = "__STATE_DIR__"
log_dir = "__LOG_DIR__"
backup_dir = "__BACKUP_DIR__"
memory_dir = "__MEMORY_DIR__"
"""
        )
        .replace("__STATE_DIR__", str(tmp_path / "state"))
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


def promote_runtime_to_ready(runtime: CoreRuntimeController) -> MarketAssessment:
    assessment = ready_market_assessment()
    runtime.process_event(assessment.to_core_event())
    runtime.process_event(assessment.to_core_event())
    return assessment


def make_market_input(
    *,
    instrument_id: str = "EURUSD",
    feed_id: str = "primary",
    news_guard_active: bool = False,
    heavy_enrichment_requested: bool = False,
) -> MarketOperationalInput:
    return MarketOperationalInput(
        instrument_id=instrument_id,
        feed_id=feed_id,
        feed_available=True,
        market_open=True,
        sample_valid=True,
        sample_age_ms=100,
        latency_ms=20,
        spread_bps=1.0,
        news_guard_active=news_guard_active,
        heavy_enrichment_requested=heavy_enrichment_requested,
    )


def test_config_defaults_to_lite_and_forces_memory_and_learn_off(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path, profile=None, memory_enabled=True))

    assert settings.profile.name == ExecutionProfile.LITE
    assert settings.profile.learn_enabled is False
    assert settings.profile.shadow_mode_enabled is False
    assert settings.memory.enabled is False
    assert settings.dashboard.surface == DashboardSurface.LITE
    assert settings.market.profile == MarketProfile.SIMPLE
    assert settings.market.instrument_scope == ("EURUSD",)
    assert settings.market.feed_scope == ("primary",)
    assert settings.market.news_guard_enabled is False
    assert settings.market.heavy_enrichment_enabled is False


def test_dash_lite_projects_operation_focus_and_blocks_learn_actions(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path, profile="lite"))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    runtime = CoreRuntimeController(settings, state_store=store)
    bridge = CoreDashBridge()
    supervisor = DashboardPermissionContext.for_role("sup-1", "supervisor")

    runtime.start()
    market_assessment = promote_runtime_to_ready(runtime)
    intent = ExecutionIntent.create(
        intent_id="intent-lite-1",
        decision_cycle_id="cycle-lite-1",
        ttl_ms=3000,
        instrument_id="EURUSD",
        side="BUY",
        target_order_type="MARKET",
        max_slippage=0.0002,
        market_snapshot_ref="market-lite-1",
        risk_snapshot_ref="risk-lite-1",
        price_reference=1.1000,
        decision_config_version="decision-v1",
    )
    report = DemoExecutionEngine(ledger_store=store).execute(
        intent,
        PreExecutionContext(
            global_state=runtime.get_public_view().state_code,
            current_mode=runtime.get_public_view().mode_code,
            risk_decision="ALLOW",
            market_state=market_assessment.market_state.value,
            market_readiness=market_assessment.readiness_state.value,
            current_executable_price=1.10005,
        ),
    )
    runtime.process_event(report.to_core_event())

    projection = bridge.project_state(runtime.get_public_view(), supervisor, runtime=runtime)
    rejection = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_REVIEW_APPROVAL",
            requested_by="sup-1",
            authorization_context={"proposal_id": "proposal-lite-1"},
        ),
        supervisor,
    )

    assert projection.global_state_model.dashboard_profile == "lite"
    assert projection.global_state_model.learn_shadow_audit is None
    assert projection.global_state_model.learn_operational_hints == ()
    assert projection.learn_query_results is None
    assert not any(
        action.startswith("LEARN_ACTION")
        for action in projection.action_availability.available_actions
    )
    assert projection.global_state_model.operation_focus is not None
    assert projection.global_state_model.operation_focus["market_runtime"]["execution_profile"] == "lite"
    assert projection.global_state_model.operation_focus["market_runtime"]["market_profile"] == "simple"
    assert projection.global_state_model.operation_focus["execution_gate"] in {"open", "standby"}
    assert projection.global_state_model.operation_focus["last_execution"]["intent_id"] == intent.intent_id
    assert projection.global_state_model.operation_focus["last_execution"]["exec_state"] == (
        report.snapshot.exec_state.value
    )
    assert rejection.accepted is False
    assert rejection.rejection_reason == "feature_disabled_for_profile"


def test_market_runtime_lite_enforces_minimal_envelope_and_projects_restrictions(
    tmp_path: Path,
) -> None:
    settings = OdinSettings.load(
        write_config(
            tmp_path,
            profile="lite",
            instrument_scope=("EURUSD", "GBPUSD"),
            feed_scope=("primary", "backup"),
            news_guard_enabled=True,
            heavy_enrichment_enabled=True,
        )
    )
    runtime = CoreRuntimeController(settings)
    bridge = CoreDashBridge()
    operator = DashboardPermissionContext.for_role("ops-1", "operator")

    runtime.start()
    runtime.ingest_market_sample(
        make_market_input(news_guard_active=True, heavy_enrichment_requested=True)
    )

    status = runtime.get_market_runtime_status()
    projection = bridge.project_state(runtime.get_public_view(), operator, runtime=runtime)
    operation_focus = projection.global_state_model.operation_focus
    assert operation_focus is not None
    market_runtime = operation_focus["market_runtime"]

    assert status.last_gate_status == "accepted"
    assert status.last_rejection_reason is None
    assert market_runtime["execution_profile"] == "lite"
    assert market_runtime["market_profile"] == "simple"
    assert market_runtime["instrument_scope"] == ["EURUSD"]
    assert market_runtime["feed_scope"] == ["primary"]
    assert market_runtime["news_guard_enabled"] is False
    assert market_runtime["heavy_enrichment_enabled"] is False
    assert "news_guard_disabled" in market_runtime["active_restrictions"]
    assert "heavy_enrichment_disabled" in market_runtime["active_restrictions"]
    assert "news_guard_forced_off" in market_runtime["applied_restrictions"]
    assert "heavy_enrichment_dropped" in market_runtime["applied_restrictions"]


def test_market_runtime_standard_accepts_configured_second_instrument_and_feed(
    tmp_path: Path,
) -> None:
    settings = OdinSettings.load(
        write_config(
            tmp_path,
            profile="standard",
            instrument_scope=("EURUSD", "GBPUSD"),
            feed_scope=("primary", "backup"),
            news_guard_enabled=True,
            heavy_enrichment_enabled=True,
        )
    )
    runtime = CoreRuntimeController(settings)
    bridge = CoreDashBridge()
    operator = DashboardPermissionContext.for_role("ops-1", "operator")

    runtime.start()
    runtime.ingest_market_sample(
        make_market_input(
            instrument_id="GBPUSD",
            feed_id="backup",
            news_guard_active=True,
            heavy_enrichment_requested=True,
        )
    )

    status = runtime.get_market_runtime_status()
    projection = bridge.project_state(runtime.get_public_view(), operator, runtime=runtime)
    operation_focus = projection.global_state_model.operation_focus
    assert operation_focus is not None
    market_runtime = operation_focus["market_runtime"]

    assert status.last_gate_status == "accepted"
    assert status.last_rejection_reason is None
    assert status.last_instrument_id == "GBPUSD"
    assert status.last_feed_id == "backup"
    assert market_runtime["execution_profile"] == "standard"
    assert market_runtime["market_profile"] == "standard"
    assert market_runtime["instrument_scope"] == ["EURUSD", "GBPUSD"]
    assert market_runtime["feed_scope"] == ["primary", "backup"]
    assert market_runtime["news_guard_enabled"] is True
    assert market_runtime["heavy_enrichment_enabled"] is True
    assert "news_guard_forced_off" not in market_runtime["applied_restrictions"]
    assert "heavy_enrichment_dropped" not in market_runtime["applied_restrictions"]


def test_state_store_migrates_legacy_schema_and_keeps_execution_ledger_queryable(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "legacy.db"
    snapshot = GlobalStateSnapshot.create(
        state_code=GlobalState.READY,
        mode_code=OperationalMode.DEMO,
        last_transition_event="legacy_seed",
        readiness_class=ReadinessClass.READY,
        integrity_class=IntegrityClass.OK,
        kill_active=False,
        active_block_count=0,
        recovery_required=False,
    )
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE state_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                created_at_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO state_snapshots VALUES (?, ?, ?)",
            (
                snapshot.snapshot_id,
                isoformat_utc(snapshot.last_transition_at_utc),
                json.dumps(snapshot.to_dict(), sort_keys=True),
            ),
        )
        connection.commit()

    store = SQLiteStateStore(db_path)
    store.initialize()

    ledger_record = DemoExecutionEngine(ledger_store=store).execute(
        ExecutionIntent.create(
            intent_id="intent-ledger-1",
            decision_cycle_id="cycle-ledger-1",
            ttl_ms=3000,
            instrument_id="EURUSD",
            side="BUY",
            target_order_type="MARKET",
            max_slippage=0.0002,
            market_snapshot_ref="market-ledger-1",
            risk_snapshot_ref="risk-ledger-1",
            price_reference=1.1000,
        ),
        PreExecutionContext(
            global_state=GlobalState.READY,
            current_mode=OperationalMode.DEMO,
            risk_decision="ALLOW",
            market_state="MS-10",
            market_readiness="READY",
            current_executable_price=1.10005,
        ),
    )

    assert store.read_schema_version() == 3
    assert store.read_latest_state_snapshot() is not None
    latest_ledger = store.read_latest_execution_ledger_record()
    assert latest_ledger is not None
    assert latest_ledger.intent_id == "intent-ledger-1"
    assert latest_ledger.exec_state == ledger_record.snapshot.exec_state
    assert store.list_execution_ledger_records(intent_id="intent-ledger-1")[0].intent_id == "intent-ledger-1"


def test_install_script_supports_dry_run_with_profiles() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            "bash",
            "INSTALL_ODIN.sh",
            "--dry-run",
            "--skip-apt",
            "--skip-systemd",
            "--profile",
            "standard",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "[odin-install] Dry-run complete. No changes were made." in result.stdout
    assert "Profile:                 standard" in result.stdout
