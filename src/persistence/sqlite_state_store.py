from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any, Callable, TypeVar

from persistence.state_store import PersistentStateStore
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
from shared.utils import isoformat_utc, utc_now


CURRENT_SCHEMA_VERSION = 3
BASE_SCHEMA_TABLES: tuple[str, ...] = (
    "state_snapshots",
    "kill_states",
    "block_vectors",
    "runtime_markers",
    "recovery_snapshots",
    "learning_history_snapshots",
    "change_proposals",
    "learn_approval_states",
    "version_snapshots",
    "shadow_sessions",
    "promotion_decisions",
    "version_activations",
    "rollback_records",
)
REQUIRED_TABLES: tuple[str, ...] = (
    *BASE_SCHEMA_TABLES,
    "learn_approval_state_history",
    "execution_ledger",
)
T = TypeVar("T")
MigrationCallable = Callable[[sqlite3.Cursor], None]


class SQLiteStateStore(PersistentStateStore):
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            self._ensure_schema_metadata_tables(cursor)
            current_version = self._read_schema_version(cursor)
            if current_version is None:
                inferred_version = self._infer_legacy_schema_version(cursor)
                self._set_schema_version(cursor, inferred_version)
                if inferred_version > 0:
                    self._record_migration(
                        cursor,
                        inferred_version,
                        f"legacy_baseline_v{inferred_version}",
                    )
                current_version = inferred_version
            for version, name, migration in self._migrations():
                if version <= current_version:
                    continue
                migration(cursor)
                self._record_migration(cursor, version, name)
                self._set_schema_version(cursor, version)
                current_version = version
            connection.commit()

    def validate_integrity(self) -> bool:
        try:
            with self._connect() as connection:
                cursor = connection.cursor()
                version = self._read_schema_version(cursor)
                if version != CURRENT_SCHEMA_VERSION:
                    return False
                for table_name in ("schema_meta", "schema_migrations", *REQUIRED_TABLES):
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (table_name,),
                    )
                    if cursor.fetchone() is None:
                        return False
        except sqlite3.DatabaseError:
            return False
        return True

    def read_schema_version(self) -> int | None:
        with self._connect() as connection:
            return self._read_schema_version(connection.cursor())

    def read_latest_state_snapshot(self) -> GlobalStateSnapshot | None:
        row = self._fetch_latest("state_snapshots")
        if row is None:
            return None
        return GlobalStateSnapshot.from_dict(json.loads(row[2]))

    def write_state_snapshot(self, snapshot: GlobalStateSnapshot) -> None:
        payload = json.dumps(snapshot.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO state_snapshots VALUES (?, ?, ?)",
                (snapshot.snapshot_id, isoformat_utc(snapshot.last_transition_at_utc), payload),
            )
            connection.commit()

    def read_kill_state(self) -> PersistentKillState | None:
        row = self._fetch_latest("kill_states")
        if row is None:
            return None
        return PersistentKillState.from_dict(json.loads(row[2]))

    def write_kill_state(self, kill_state: PersistentKillState) -> None:
        payload = json.dumps(kill_state.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO kill_states VALUES (?, ?, ?)",
                (kill_state.kill_id, isoformat_utc(kill_state.activated_at_utc), payload),
            )
            connection.commit()

    def read_latest_block_vector(self) -> ActiveBlockVector | None:
        row = self._fetch_latest("block_vectors")
        if row is None:
            return None
        return ActiveBlockVector.from_dict(json.loads(row[2]))

    def write_block_vector(self, vector: ActiveBlockVector) -> None:
        payload = json.dumps(vector.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO block_vectors VALUES (?, ?, ?)",
                (vector.vector_id, isoformat_utc(vector.updated_at_utc), payload),
            )
            connection.commit()

    def mark_startup_in_progress(self, startup_id: str, happened_at_utc: datetime) -> None:
        payload = json.dumps(
            {
                "marker_id": startup_id,
                "clean_shutdown": False,
                "startup_in_progress": True,
                "happened_at_utc": isoformat_utc(happened_at_utc),
            },
            sort_keys=True,
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO runtime_markers VALUES (?, ?, ?)",
                (startup_id, isoformat_utc(happened_at_utc), payload),
            )
            connection.commit()

    def mark_clean_shutdown(self, marker_id: str, happened_at_utc: datetime) -> None:
        payload = json.dumps(
            {
                "marker_id": marker_id,
                "clean_shutdown": True,
                "startup_in_progress": False,
                "happened_at_utc": isoformat_utc(happened_at_utc),
            },
            sort_keys=True,
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO runtime_markers VALUES (?, ?, ?)",
                (marker_id, isoformat_utc(happened_at_utc), payload),
            )
            connection.commit()

    def read_shutdown_marker(self) -> ShutdownMarker | None:
        row = self._fetch_latest("runtime_markers")
        if row is None:
            return None
        return ShutdownMarker.from_dict(json.loads(row[2]))

    def read_latest_recovery_snapshot(self) -> RecoverySnapshot | None:
        row = self._fetch_latest("recovery_snapshots")
        if row is None:
            return None
        return RecoverySnapshot.from_dict(json.loads(row[2]))

    def write_recovery_snapshot(self, snapshot: RecoverySnapshot) -> None:
        payload = json.dumps(snapshot.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO recovery_snapshots VALUES (?, ?, ?)",
                (snapshot.recovery_snapshot_id, isoformat_utc(snapshot.created_at_utc), payload),
            )
            connection.commit()

    def read_latest_learning_history_snapshot(self) -> LearningHistorySnapshot | None:
        row = self._fetch_latest("learning_history_snapshots")
        if row is None:
            return None
        return LearningHistorySnapshot.from_dict(json.loads(row[2]))

    def write_learning_history_snapshot(self, snapshot: LearningHistorySnapshot) -> None:
        payload = json.dumps(snapshot.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO learning_history_snapshots VALUES (?, ?, ?)",
                (snapshot.history_snapshot_id, isoformat_utc(snapshot.created_at_utc), payload),
            )
            connection.commit()

    def read_change_proposal(self, proposal_id: str) -> ChangeProposal | None:
        payload = self._fetch_payload_by_key(
            "SELECT payload_json FROM change_proposals WHERE proposal_id = ?",
            (proposal_id,),
        )
        if payload is None:
            return None
        return ChangeProposal.from_dict(json.loads(payload))

    def read_latest_change_proposal(self) -> ChangeProposal | None:
        row = self._fetch_latest("change_proposals")
        if row is None:
            return None
        return ChangeProposal.from_dict(json.loads(row[2]))

    def write_change_proposal(self, proposal: ChangeProposal) -> None:
        payload = json.dumps(proposal.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO change_proposals VALUES (?, ?, ?)",
                (proposal.proposal_id, isoformat_utc(proposal.created_at_utc), payload),
            )
            connection.commit()

    def list_change_proposals(
        self,
        *,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[ChangeProposal, ...]:
        return self._list_records(
            table_name="change_proposals",
            order_by="created_at_utc ASC, proposal_id ASC",
            parser=ChangeProposal.from_dict,
            window_column="created_at_utc",
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )

    def read_approval_state(self, proposal_id: str) -> ApprovalState | None:
        payload = self._fetch_payload_by_key(
            "SELECT payload_json FROM learn_approval_states WHERE proposal_id = ?",
            (proposal_id,),
        )
        if payload is None:
            return None
        return ApprovalState.from_dict(json.loads(payload))

    def write_approval_state(self, approval_state: ApprovalState) -> None:
        payload = json.dumps(approval_state.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO learn_approval_states VALUES (?, ?, ?)",
                (
                    approval_state.proposal_id,
                    isoformat_utc(approval_state.updated_at_utc),
                    payload,
                ),
            )
            connection.execute(
                """
                INSERT INTO learn_approval_state_history (
                    proposal_id,
                    updated_at_utc,
                    payload_json
                )
                VALUES (?, ?, ?)
                """,
                (
                    approval_state.proposal_id,
                    isoformat_utc(approval_state.updated_at_utc),
                    payload,
                ),
            )
            connection.commit()

    def list_approval_states(
        self,
        *,
        proposal_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[ApprovalState, ...]:
        clauses: list[str] = []
        params: list[object] = []
        if proposal_id is not None:
            clauses.append("proposal_id = ?")
            params.append(proposal_id)
        return self._list_records(
            table_name="learn_approval_state_history",
            order_by="updated_at_utc ASC, history_id ASC",
            parser=ApprovalState.from_dict,
            clauses=clauses,
            params=params,
            window_column="updated_at_utc",
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )

    def read_version_snapshot(self, snapshot_id: str) -> VersionSnapshot | None:
        payload = self._fetch_payload_by_key(
            "SELECT payload_json FROM version_snapshots WHERE snapshot_id = ?",
            (snapshot_id,),
        )
        if payload is None:
            return None
        return VersionSnapshot.from_dict(json.loads(payload))

    def read_latest_version_snapshot_for_version(
        self,
        version_id: str,
        *,
        snapshot_type: LearnSnapshotType | None = None,
        recoverable_only: bool = False,
    ) -> VersionSnapshot | None:
        query = (
            "SELECT payload_json FROM version_snapshots WHERE version_id = ?"
        )
        params: list[object] = [version_id]
        if snapshot_type is not None:
            query += " AND snapshot_type = ?"
            params.append(snapshot_type.value)
        if recoverable_only:
            query += " AND is_recoverable = 1"
        query += " ORDER BY created_at_utc DESC LIMIT 1"
        payload = self._fetch_payload_by_key(query, tuple(params))
        if payload is None:
            return None
        return VersionSnapshot.from_dict(json.loads(payload))

    def write_version_snapshot(self, snapshot: VersionSnapshot) -> None:
        payload = json.dumps(snapshot.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO version_snapshots VALUES (?, ?, ?, ?, ?, ?)",
                (
                    snapshot.snapshot_id,
                    isoformat_utc(snapshot.created_at_utc),
                    snapshot.version_id,
                    snapshot.snapshot_type.value,
                    int(snapshot.is_recoverable),
                    payload,
                ),
            )
            connection.commit()

    def read_latest_shadow_session_for_proposal(
        self, proposal_id: str
    ) -> ShadowEvaluationSession | None:
        payload = self._fetch_payload_by_key(
            """
            SELECT payload_json
            FROM shadow_sessions
            WHERE proposal_id = ?
            ORDER BY created_at_utc DESC
            LIMIT 1
            """,
            (proposal_id,),
        )
        if payload is None:
            return None
        return ShadowEvaluationSession.from_dict(json.loads(payload))

    def write_shadow_session(self, session: ShadowEvaluationSession) -> None:
        payload = json.dumps(session.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO shadow_sessions VALUES (?, ?, ?, ?)",
                (
                    session.shadow_session_id,
                    isoformat_utc(session.started_at_utc),
                    session.proposal_id,
                    payload,
                ),
            )
            connection.commit()

    def list_shadow_sessions(
        self,
        *,
        proposal_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[ShadowEvaluationSession, ...]:
        clauses: list[str] = []
        params: list[object] = []
        if proposal_id is not None:
            clauses.append("proposal_id = ?")
            params.append(proposal_id)
        return self._list_records(
            table_name="shadow_sessions",
            order_by="created_at_utc ASC, shadow_session_id ASC",
            parser=ShadowEvaluationSession.from_dict,
            clauses=clauses,
            params=params,
            window_column="created_at_utc",
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )

    def read_latest_promotion_decision(
        self,
        proposal_id: str | None = None,
    ) -> PromotionDecision | None:
        query = "SELECT payload_json FROM promotion_decisions"
        params: tuple[object, ...] = tuple()
        if proposal_id is not None:
            query += " WHERE proposal_id = ?"
            params = (proposal_id,)
        query += " ORDER BY evaluated_at_utc DESC LIMIT 1"
        payload = self._fetch_payload_by_key(query, params)
        if payload is None:
            return None
        return PromotionDecision.from_dict(json.loads(payload))

    def write_promotion_decision(self, decision: PromotionDecision) -> None:
        payload = json.dumps(decision.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO promotion_decisions VALUES (?, ?, ?, ?)",
                (
                    decision.promotion_id,
                    isoformat_utc(decision.evaluated_at_utc),
                    decision.proposal_id,
                    payload,
                ),
            )
            connection.commit()

    def list_promotion_decisions(
        self,
        *,
        proposal_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[PromotionDecision, ...]:
        clauses: list[str] = []
        params: list[object] = []
        if proposal_id is not None:
            clauses.append("proposal_id = ?")
            params.append(proposal_id)
        return self._list_records(
            table_name="promotion_decisions",
            order_by="evaluated_at_utc ASC, promotion_id ASC",
            parser=PromotionDecision.from_dict,
            clauses=clauses,
            params=params,
            window_column="evaluated_at_utc",
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )

    def read_latest_version_activation(self) -> VersionActivationRecord | None:
        payload = self._fetch_payload_by_key(
            """
            SELECT payload_json
            FROM version_activations
            ORDER BY activated_at_utc DESC
            LIMIT 1
            """
        )
        if payload is None:
            return None
        return VersionActivationRecord.from_dict(json.loads(payload))

    def write_version_activation(self, activation: VersionActivationRecord) -> None:
        payload = json.dumps(activation.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO version_activations VALUES (?, ?, ?, ?, ?)",
                (
                    activation.activation_id,
                    isoformat_utc(activation.activated_at_utc),
                    activation.version_id,
                    activation.previous_version_id,
                    payload,
                ),
            )
            connection.commit()

    def read_latest_rollback_record(self) -> RollbackRecord | None:
        payload = self._fetch_payload_by_key(
            """
            SELECT payload_json
            FROM rollback_records
            ORDER BY triggered_at_utc DESC
            LIMIT 1
            """
        )
        if payload is None:
            return None
        return RollbackRecord.from_dict(json.loads(payload))

    def write_rollback_record(self, rollback_record: RollbackRecord) -> None:
        payload = json.dumps(rollback_record.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO rollback_records VALUES (?, ?, ?, ?, ?, ?)",
                (
                    rollback_record.rollback_id,
                    isoformat_utc(rollback_record.triggered_at_utc),
                    rollback_record.from_version_id,
                    rollback_record.to_version_id,
                    rollback_record.to_snapshot_id,
                    payload,
                ),
            )
            connection.commit()

    def list_rollback_records(
        self,
        *,
        version_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[RollbackRecord, ...]:
        clauses: list[str] = []
        params: list[object] = []
        if version_id is not None:
            clauses.append("(from_version_id = ? OR to_version_id = ?)")
            params.extend((version_id, version_id))
        return self._list_records(
            table_name="rollback_records",
            order_by="triggered_at_utc ASC, rollback_id ASC",
            parser=RollbackRecord.from_dict,
            clauses=clauses,
            params=params,
            window_column="triggered_at_utc",
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )

    def read_latest_execution_ledger_record(self) -> ExecutionLedgerRecord | None:
        payload = self._fetch_payload_by_key(
            """
            SELECT payload_json
            FROM execution_ledger
            ORDER BY recorded_at_utc DESC
            LIMIT 1
            """
        )
        if payload is None:
            return None
        return ExecutionLedgerRecord.from_dict(json.loads(payload))

    def write_execution_ledger_record(self, record: ExecutionLedgerRecord) -> None:
        payload = json.dumps(record.to_dict(), sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO execution_ledger VALUES (?, ?, ?, ?, ?)",
                (
                    record.ledger_id,
                    isoformat_utc(record.recorded_at_utc),
                    record.intent_id,
                    record.request_id,
                    payload,
                ),
            )
            connection.commit()

    def list_execution_ledger_records(
        self,
        *,
        intent_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[ExecutionLedgerRecord, ...]:
        clauses: list[str] = []
        params: list[object] = []
        if intent_id is not None:
            clauses.append("intent_id = ?")
            params.append(intent_id)
        return self._list_records(
            table_name="execution_ledger",
            order_by="recorded_at_utc ASC, ledger_id ASC",
            parser=ExecutionLedgerRecord.from_dict,
            clauses=clauses,
            params=params,
            window_column="recorded_at_utc",
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def _migrations(self) -> tuple[tuple[int, str, MigrationCallable], ...]:
        return (
            (1, "base_schema", self._apply_migration_1_base_schema),
            (2, "learn_approval_history", self._apply_migration_2_learn_approval_history),
            (3, "execution_ledger", self._apply_migration_3_execution_ledger),
        )

    def _ensure_schema_metadata_tables(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                schema_key TEXT PRIMARY KEY,
                schema_version INTEGER NOT NULL,
                updated_at_utc TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_version INTEGER PRIMARY KEY,
                migration_name TEXT NOT NULL,
                applied_at_utc TEXT NOT NULL
            )
            """
        )

    def _read_schema_version(self, cursor: sqlite3.Cursor) -> int | None:
        cursor.execute(
            """
            SELECT schema_version
            FROM schema_meta
            WHERE schema_key = 'state_store'
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return int(row[0])

    def _set_schema_version(self, cursor: sqlite3.Cursor, version: int) -> None:
        cursor.execute(
            """
            INSERT OR REPLACE INTO schema_meta (
                schema_key,
                schema_version,
                updated_at_utc
            )
            VALUES ('state_store', ?, ?)
            """,
            (version, isoformat_utc(utc_now())),
        )

    def _record_migration(
        self,
        cursor: sqlite3.Cursor,
        version: int,
        name: str,
    ) -> None:
        cursor.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (
                migration_version,
                migration_name,
                applied_at_utc
            )
            VALUES (?, ?, ?)
            """,
            (version, name, isoformat_utc(utc_now())),
        )

    def _infer_legacy_schema_version(self, cursor: sqlite3.Cursor) -> int:
        existing_tables = self._list_existing_tables(cursor)
        domain_tables = existing_tables.difference({"schema_meta", "schema_migrations"})
        if not domain_tables:
            return 0
        if not set(BASE_SCHEMA_TABLES).issubset(existing_tables):
            return 0
        if "execution_ledger" in existing_tables:
            return 3
        if "learn_approval_state_history" in existing_tables:
            return 2
        return 1

    def _list_existing_tables(self, cursor: sqlite3.Cursor) -> set[str]:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return {str(row[0]) for row in cursor.fetchall()}

    def _apply_migration_1_base_schema(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS state_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                created_at_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS kill_states (
                kill_id TEXT PRIMARY KEY,
                created_at_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS block_vectors (
                vector_id TEXT PRIMARY KEY,
                created_at_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_markers (
                marker_id TEXT PRIMARY KEY,
                happened_at_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recovery_snapshots (
                recovery_snapshot_id TEXT PRIMARY KEY,
                created_at_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_history_snapshots (
                history_snapshot_id TEXT PRIMARY KEY,
                created_at_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS change_proposals (
                proposal_id TEXT PRIMARY KEY,
                created_at_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learn_approval_states (
                proposal_id TEXT PRIMARY KEY,
                updated_at_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS version_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                created_at_utc TEXT NOT NULL,
                version_id TEXT NOT NULL,
                snapshot_type TEXT NOT NULL,
                is_recoverable INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS shadow_sessions (
                shadow_session_id TEXT PRIMARY KEY,
                created_at_utc TEXT NOT NULL,
                proposal_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS promotion_decisions (
                promotion_id TEXT PRIMARY KEY,
                evaluated_at_utc TEXT NOT NULL,
                proposal_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS version_activations (
                activation_id TEXT PRIMARY KEY,
                activated_at_utc TEXT NOT NULL,
                version_id TEXT NOT NULL,
                previous_version_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rollback_records (
                rollback_id TEXT PRIMARY KEY,
                triggered_at_utc TEXT NOT NULL,
                from_version_id TEXT NOT NULL,
                to_version_id TEXT NOT NULL,
                to_snapshot_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )

    def _apply_migration_2_learn_approval_history(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learn_approval_state_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposal_id TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )

    def _apply_migration_3_execution_ledger(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_ledger (
                ledger_id TEXT PRIMARY KEY,
                recorded_at_utc TEXT NOT NULL,
                intent_id TEXT NOT NULL,
                request_id TEXT,
                payload_json TEXT NOT NULL
            )
            """
        )

    def _build_select_payload_query(
        self,
        table_name: str,
        *,
        clauses: list[str],
        order_by: str,
    ) -> str:
        query = f"SELECT payload_json FROM {table_name}"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += f" ORDER BY {order_by}"
        return query

    def _append_time_window_filters(
        self,
        clauses: list[str],
        params: list[object],
        *,
        column_name: str,
        start_at_utc: datetime | None,
        end_at_utc: datetime | None,
    ) -> None:
        if start_at_utc is not None:
            clauses.append(f"{column_name} >= ?")
            params.append(isoformat_utc(start_at_utc))
        if end_at_utc is not None:
            clauses.append(f"{column_name} <= ?")
            params.append(isoformat_utc(end_at_utc))

    def _fetch_latest(self, table_name: str) -> tuple[str, str, str] | None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"SELECT * FROM {table_name} ORDER BY created_at_utc DESC LIMIT 1"
                if table_name != "runtime_markers"
                else "SELECT * FROM runtime_markers ORDER BY happened_at_utc DESC LIMIT 1"
            )
            row = cursor.fetchone()
        return row

    def _fetch_payload_by_key(
        self,
        query: str,
        params: tuple[object, ...] = tuple(),
    ) -> str | None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
        if row is None:
            return None
        return str(row[0])

    def _fetch_payloads(
        self,
        query: str,
        params: tuple[object, ...] = tuple(),
    ) -> tuple[str, ...]:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return tuple(str(row[0]) for row in rows)

    def _list_records(
        self,
        *,
        table_name: str,
        order_by: str,
        parser: Callable[[dict[str, Any]], T],
        clauses: list[str] | None = None,
        params: list[object] | None = None,
        window_column: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[T, ...]:
        query_clauses = list(clauses or [])
        query_params = list(params or [])
        if window_column is not None:
            self._append_time_window_filters(
                query_clauses,
                query_params,
                column_name=window_column,
                start_at_utc=start_at_utc,
                end_at_utc=end_at_utc,
            )
        payloads = self._fetch_payloads(
            self._build_select_payload_query(
                table_name,
                clauses=query_clauses,
                order_by=order_by,
            ),
            tuple(query_params),
        )
        return tuple(parser(json.loads(payload)) for payload in payloads)
