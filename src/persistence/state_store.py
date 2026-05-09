from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from shared.contracts import (
    ActiveBlockVector,
    ApprovalState,
    ChangeProposal,
    ExecutionLedgerRecord,
    GlobalStateSnapshot,
    LearningHistorySnapshot,
    PersistentKillState,
    PromotionDecision,
    RecoverySnapshot,
    RollbackRecord,
    ShadowEvaluationSession,
    ShutdownMarker,
    VersionActivationRecord,
    VersionSnapshot,
)
from shared.enums import LearnSnapshotType


class PersistentStateStore(ABC):
    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def validate_integrity(self) -> bool: ...

    @abstractmethod
    def read_latest_state_snapshot(self) -> GlobalStateSnapshot | None: ...

    @abstractmethod
    def write_state_snapshot(self, snapshot: GlobalStateSnapshot) -> None: ...

    @abstractmethod
    def read_kill_state(self) -> PersistentKillState | None: ...

    @abstractmethod
    def write_kill_state(self, kill_state: PersistentKillState) -> None: ...

    @abstractmethod
    def read_latest_block_vector(self) -> ActiveBlockVector | None: ...

    @abstractmethod
    def write_block_vector(self, vector: ActiveBlockVector) -> None: ...

    @abstractmethod
    def mark_startup_in_progress(self, startup_id: str, happened_at_utc: datetime) -> None: ...

    @abstractmethod
    def mark_clean_shutdown(self, marker_id: str, happened_at_utc: datetime) -> None: ...

    @abstractmethod
    def read_shutdown_marker(self) -> ShutdownMarker | None: ...

    @abstractmethod
    def read_latest_recovery_snapshot(self) -> RecoverySnapshot | None: ...

    @abstractmethod
    def write_recovery_snapshot(self, snapshot: RecoverySnapshot) -> None: ...

    @abstractmethod
    def read_latest_learning_history_snapshot(self) -> LearningHistorySnapshot | None: ...

    @abstractmethod
    def write_learning_history_snapshot(self, snapshot: LearningHistorySnapshot) -> None: ...

    @abstractmethod
    def read_change_proposal(self, proposal_id: str) -> ChangeProposal | None: ...

    @abstractmethod
    def read_latest_change_proposal(self) -> ChangeProposal | None: ...

    @abstractmethod
    def write_change_proposal(self, proposal: ChangeProposal) -> None: ...

    @abstractmethod
    def list_change_proposals(
        self,
        *,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[ChangeProposal, ...]: ...

    @abstractmethod
    def read_approval_state(self, proposal_id: str) -> ApprovalState | None: ...

    @abstractmethod
    def write_approval_state(self, approval_state: ApprovalState) -> None: ...

    @abstractmethod
    def list_approval_states(
        self,
        *,
        proposal_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[ApprovalState, ...]: ...

    @abstractmethod
    def read_version_snapshot(self, snapshot_id: str) -> VersionSnapshot | None: ...

    @abstractmethod
    def read_latest_version_snapshot_for_version(
        self,
        version_id: str,
        *,
        snapshot_type: LearnSnapshotType | None = None,
        recoverable_only: bool = False,
    ) -> VersionSnapshot | None: ...

    @abstractmethod
    def write_version_snapshot(self, snapshot: VersionSnapshot) -> None: ...

    @abstractmethod
    def read_latest_shadow_session_for_proposal(
        self, proposal_id: str
    ) -> ShadowEvaluationSession | None: ...

    @abstractmethod
    def write_shadow_session(self, session: ShadowEvaluationSession) -> None: ...

    @abstractmethod
    def list_shadow_sessions(
        self,
        *,
        proposal_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[ShadowEvaluationSession, ...]: ...

    @abstractmethod
    def read_latest_promotion_decision(
        self, proposal_id: str | None = None
    ) -> PromotionDecision | None: ...

    @abstractmethod
    def write_promotion_decision(self, decision: PromotionDecision) -> None: ...

    @abstractmethod
    def list_promotion_decisions(
        self,
        *,
        proposal_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[PromotionDecision, ...]: ...

    @abstractmethod
    def read_latest_version_activation(self) -> VersionActivationRecord | None: ...

    @abstractmethod
    def write_version_activation(self, activation: VersionActivationRecord) -> None: ...

    @abstractmethod
    def read_latest_rollback_record(self) -> RollbackRecord | None: ...

    @abstractmethod
    def write_rollback_record(self, rollback_record: RollbackRecord) -> None: ...

    @abstractmethod
    def list_rollback_records(
        self,
        *,
        version_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[RollbackRecord, ...]: ...

    @abstractmethod
    def read_latest_execution_ledger_record(self) -> ExecutionLedgerRecord | None: ...

    @abstractmethod
    def write_execution_ledger_record(self, record: ExecutionLedgerRecord) -> None: ...

    @abstractmethod
    def list_execution_ledger_records(
        self,
        *,
        intent_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[ExecutionLedgerRecord, ...]: ...
