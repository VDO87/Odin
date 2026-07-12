"""A21 deterministic mock strategy context snapshot builder."""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from odin.contracts.events import (
    STRATEGY_CONTEXT_SNAPSHOT_BUILT,
    STRATEGY_CONTEXT_SNAPSHOT_DECISION_BLOCKED,
    STRATEGY_CONTEXT_SNAPSHOT_EXECUTION_BLOCKED,
    STRATEGY_CONTEXT_SNAPSHOT_INVALID,
    STRATEGY_CONTEXT_SNAPSHOT_REQUESTED,
    OdinEvent,
)
from odin.contracts.strategy_context_snapshot import StrategyContextSnapshot
from odin.decision.observation_frame_quality import observation_frame_quality_status
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


BLOCKERS = (
    "decision_use_blocked",
    "risk_gate_blocked",
    "shadow_proposal_blocked",
    "execution_disabled",
    "real_trading_disabled",
)

FINGERPRINT_FIELDS = (
    "selected_source",
    "primary_symbol",
    "feed_quality_status",
    "data_quality_status",
    "frame_quality_status",
    "strategy_status",
    "decision_intent_status",
    "risk_status",
    "shadow_proposal_status",
    "gates_count",
    "all_gates_passed",
)


class MockStrategyContextSnapshotBuilder:
    component = "strategy_context_snapshot"
    snapshot_mode = "MOCK_OBSERVATION_ONLY"
    snapshot_version = "A21.v1"

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

    def report(self, quality_report: dict[str, object] | None = None) -> dict[str, object]:
        self._audit(STRATEGY_CONTEXT_SNAPSHOT_REQUESTED, {})
        quality = quality_report or observation_frame_quality_status(
            log_path=self.log_path,
            sqlite_path=self.sqlite_path,
        )
        valid = _quality_is_valid(quality)
        blockers = BLOCKERS if valid else BLOCKERS + ("a20_quality_not_approved",)
        status = "OK" if valid else "BLOCKED"
        reason = "strategy_context_snapshot_mock_ready" if valid else "a20_quality_invalid"
        fingerprint = strategy_context_fingerprint(quality)
        snapshot = StrategyContextSnapshot(
            component=self.component,
            status=status,
            snapshot_mode=self.snapshot_mode,
            snapshot_version=self.snapshot_version,
            selected_source=str(quality.get("selected_source", "")),
            primary_symbol=str(quality.get("primary_symbol", "")),
            feed_quality_status=str(quality.get("feed_quality_status", "UNKNOWN")),
            data_quality_status=str(quality.get("data_quality_status", "UNKNOWN")),
            frame_quality_status=str(quality.get("frame_quality_status", "INVALID")),
            strategy_status=str(quality.get("strategy_status", "UNKNOWN")),
            decision_intent_status=str(quality.get("decision_intent_status", "NO_DECISION")),
            risk_status=str(quality.get("risk_status", "BLOCKED")),
            shadow_proposal_status=str(quality.get("shadow_proposal_status", "BLOCKED")),
            quality_gates_count=_safe_int(quality.get("gates_count")),
            quality_gates_passed=quality.get("all_gates_passed") is True,
            context_fingerprint=fingerprint,
            safe_to_use_for_decision=False,
            decision_generated=False,
            proposal_generated=False,
            risk_approved=False,
            execution_allowed=False,
            safe_to_trade=False,
            real_trading=False,
            reason=reason,
            blockers=blockers,
            notes=(
                "A21 freezes approved observational context only.",
                "Snapshot quality never authorizes decisions, risk, proposals, or execution.",
            ),
        ).to_dict()
        self._audit(
            STRATEGY_CONTEXT_SNAPSHOT_BUILT if valid else STRATEGY_CONTEXT_SNAPSHOT_INVALID,
            {"status": status, "context_fingerprint": fingerprint},
        )
        self._audit(STRATEGY_CONTEXT_SNAPSHOT_DECISION_BLOCKED, {"decision_generated": False})
        self._audit(STRATEGY_CONTEXT_SNAPSHOT_EXECUTION_BLOCKED, {"execution_allowed": False})
        return snapshot

    def _audit(self, event_name: str, payload: dict[str, object]) -> None:
        event = OdinEvent.create(
            run_id=self.run_id,
            component="odin.strategy_context_snapshot",
            event=event_name,
            payload=payload,
        )
        self.logger.write(event)
        self.store.record_event(event)


def strategy_context_snapshot_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
    quality_report: dict[str, object] | None = None,
) -> dict[str, object]:
    return MockStrategyContextSnapshotBuilder(
        log_path=log_path,
        sqlite_path=sqlite_path,
    ).report(quality_report)


def strategy_context_fingerprint(quality_report: dict[str, object]) -> str:
    canonical = {field: quality_report.get(field) for field in FINGERPRINT_FIELDS}
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _quality_is_valid(quality: dict[str, object]) -> bool:
    critical_flags_are_false = all(
        quality.get(field) is False
        for field in (
            "safe_to_use_for_decision",
            "decision_generated",
            "trade" + "_proposal_generated",
            "risk_approved",
            "execution_allowed",
            "safe_to_trade",
            "real_trading",
        )
    )
    return (
        quality.get("status") == "OK"
        and quality.get("frame_quality_status") == "OK"
        and quality.get("all_gates_passed") is True
        and critical_flags_are_false
    )


def _safe_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0
