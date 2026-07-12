"""A22 fail-closed quality gate for the A21 strategy context snapshot."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    STRATEGY_CONTEXT_SNAPSHOT_QUALITY_BLOCKED,
    STRATEGY_CONTEXT_SNAPSHOT_QUALITY_DECISION_BLOCKED,
    STRATEGY_CONTEXT_SNAPSHOT_QUALITY_PASS,
    STRATEGY_CONTEXT_SNAPSHOT_QUALITY_REQUESTED,
    OdinEvent,
)
from odin.contracts.strategy_context_snapshot_quality import StrategyContextSnapshotQualityReport
from odin.decision.strategy_context_snapshot import (
    FINGERPRINT_FIELDS,
    strategy_context_fingerprint,
    strategy_context_snapshot_status,
)
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


REQUIRED_FIELDS = (
    "component",
    "status",
    "snapshot_mode",
    "snapshot_version",
    "selected_source",
    "primary_symbol",
    "feed_quality_status",
    "data_quality_status",
    "frame_quality_status",
    "strategy_status",
    "decision_intent_status",
    "risk_status",
    "shadow_proposal_status",
    "quality_gates_count",
    "quality_gates_passed",
    "context_fingerprint",
    "safe_to_use_for_decision",
    "decision_generated",
    "trade" + "_proposal_generated",
    "risk_approved",
    "execution_allowed",
    "safe_to_trade",
    "real_trading",
)

CRITICAL_FLAGS = (
    "safe_to_use_for_decision",
    "decision_generated",
    "trade" + "_proposal_generated",
    "risk_approved",
    "execution_allowed",
    "safe_to_trade",
    "real_trading",
)

GATES = (
    "required_fields_present",
    "schema_valid",
    "snapshot_mode_valid",
    "snapshot_version_valid",
    "source_present",
    "symbol_present",
    "fingerprint_valid",
    "quality_gates_passed",
    "flags_blocked",
)


class StrategyContextSnapshotQualityGate:
    component = "strategy_context_snapshot_quality"
    quality_mode = "SNAPSHOT_QUALITY_GATE"
    quality_version = "A22.v1"

    def __init__(
        self,
        *,
        log_path: str = "logs/odin_events.jsonl",
        sqlite_path: str = "runtime/odin.sqlite",
    ) -> None:
        self.log_path = log_path
        self.sqlite_path = sqlite_path
        self.run_id = str(uuid4())
        self.logger = JsonlLogger(log_path)
        self.store = SQLiteStore(sqlite_path)
        self.logger.initialize()
        self.store.initialize()

    def report(self, snapshot: dict[str, object] | None = None) -> dict[str, object]:
        self._audit(STRATEGY_CONTEXT_SNAPSHOT_QUALITY_REQUESTED, {})
        candidate = snapshot or strategy_context_snapshot_status(
            log_path=self.log_path,
            sqlite_path=self.sqlite_path,
        )
        report = build_strategy_context_snapshot_quality_report(candidate)
        event_name = (
            STRATEGY_CONTEXT_SNAPSHOT_QUALITY_PASS
            if report["status"] == "OK"
            else STRATEGY_CONTEXT_SNAPSHOT_QUALITY_BLOCKED
        )
        self._audit(event_name, {"status": report["status"], "blockers": report["blockers"]})
        self._audit(
            STRATEGY_CONTEXT_SNAPSHOT_QUALITY_DECISION_BLOCKED,
            {"safe_to_use_for_decision": False, "decision_generated": False},
        )
        return report

    def _audit(self, event_name: str, payload: dict[str, object]) -> None:
        event = OdinEvent.create(
            run_id=self.run_id,
            component="odin.strategy_context_snapshot_quality",
            event=event_name,
            payload=payload,
        )
        self.logger.write(event)
        self.store.record_event(event)


def strategy_context_snapshot_quality_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
    snapshot: dict[str, object] | None = None,
) -> dict[str, object]:
    return StrategyContextSnapshotQualityGate(
        log_path=log_path,
        sqlite_path=sqlite_path,
    ).report(snapshot)


def build_strategy_context_snapshot_quality_report(snapshot: dict[str, object]) -> dict[str, object]:
    missing = [field for field in REQUIRED_FIELDS if field not in snapshot]
    required_fields_present = not missing
    schema_valid = _schema_is_valid(snapshot)
    snapshot_mode_valid = snapshot.get("snapshot_mode") == "MOCK_OBSERVATION_ONLY"
    snapshot_version_valid = snapshot.get("snapshot_version") == "A21.v1"
    source_present = _text_present(snapshot.get("selected_source"))
    symbol_present = _text_present(snapshot.get("primary_symbol"))
    recomputed = _recompute_fingerprint(snapshot) if required_fields_present else ""
    fingerprint_valid = bool(recomputed) and snapshot.get("context_fingerprint") == recomputed
    quality_passed = snapshot.get("quality_gates_passed") is True
    flags_blocked = all(snapshot.get(flag) is False for flag in CRITICAL_FLAGS)
    gate_results = {
        "required_fields_present": required_fields_present,
        "schema_valid": schema_valid,
        "snapshot_mode_valid": snapshot_mode_valid,
        "snapshot_version_valid": snapshot_version_valid,
        "source_present": source_present,
        "symbol_present": symbol_present,
        "fingerprint_valid": fingerprint_valid,
        "quality_gates_passed": quality_passed,
        "flags_blocked": flags_blocked,
    }
    blockers = tuple(name for name, passed in gate_results.items() if not passed)
    status = "OK" if not blockers else "BLOCKED"
    reason = "strategy_context_snapshot_quality_passed" if status == "OK" else "strategy_context_snapshot_quality_blocked"
    report = StrategyContextSnapshotQualityReport(
        component="strategy_context_snapshot_quality",
        status=status,
        quality_mode="SNAPSHOT_QUALITY_GATE",
        quality_version="A22.v1",
        snapshot_mode=str(snapshot.get("snapshot_mode", "")),
        snapshot_version=str(snapshot.get("snapshot_version", "")),
        selected_source=str(snapshot.get("selected_source", "")),
        primary_symbol=str(snapshot.get("primary_symbol", "")),
        context_fingerprint=str(snapshot.get("context_fingerprint", "")),
        recomputed_fingerprint=recomputed,
        fingerprint_valid=fingerprint_valid,
        schema_valid=schema_valid,
        required_fields_present=required_fields_present,
        quality_gates_passed=quality_passed,
        flags_blocked=flags_blocked,
        gates_count=len(GATES),
        gates_passed=sum(1 for passed in gate_results.values() if passed),
        safe_to_use_for_decision=False,
        decision_generated=False,
        proposal_generated=False,
        risk_approved=False,
        execution_allowed=False,
        safe_to_trade=False,
        real_trading=False,
        reason=reason,
        gates=GATES,
        blockers=blockers,
        notes=(
            "A22 validates A21 snapshot consistency only.",
            "Passing quality never authorizes decisions, risk, proposals, or execution.",
        ),
    )
    return report.to_dict()


def _recompute_fingerprint(snapshot: dict[str, object]) -> str:
    quality = {
        "gates_count": snapshot.get("quality_gates_count"),
        "all_gates_passed": snapshot.get("quality_gates_passed"),
    }
    for field in FINGERPRINT_FIELDS:
        if field not in quality:
            quality[field] = snapshot.get(field)
    return strategy_context_fingerprint(quality)


def _schema_is_valid(snapshot: dict[str, object]) -> bool:
    text_fields = (
        "component",
        "status",
        "snapshot_mode",
        "snapshot_version",
        "selected_source",
        "primary_symbol",
        "context_fingerprint",
    )
    bool_fields = ("quality_gates_passed",) + CRITICAL_FLAGS
    return (
        all(isinstance(snapshot.get(field), str) for field in text_fields)
        and isinstance(snapshot.get("quality_gates_count"), int)
        and not isinstance(snapshot.get("quality_gates_count"), bool)
        and all(isinstance(snapshot.get(field), bool) for field in bool_fields)
    )


def _text_present(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
