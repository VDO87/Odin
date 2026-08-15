"""SQLite storage for A1 audit state."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from odin.contracts.events import OdinEvent
from odin.contracts.state import OdinState


class SQLiteStore:
    def __init__(self, path: Path | str = "runtime/odin.sqlite") -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    @contextmanager
    def _managed_connection(self):
        """Commit/rollback and always close the SQLite descriptor."""
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> bool:
        with self._managed_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS system_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    corr_id TEXT,
                    component TEXT NOT NULL,
                    event TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    mode TEXT,
                    symbol TEXT,
                    safe_to_trade INTEGER NOT NULL,
                    reason TEXT,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS validations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    safe_to_trade INTEGER NOT NULL,
                    real_trading INTEGER NOT NULL,
                    risk_state TEXT NOT NULL,
                    hermes_mode TEXT NOT NULL,
                    jsonl_logger_ready INTEGER NOT NULL,
                    sqlite_initialized INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS hermes_agents (
                    name TEXT PRIMARY KEY,
                    purpose TEXT NOT NULL,
                    preferred_route TEXT NOT NULL,
                    model_tier TEXT NOT NULL,
                    allowed_actions_json TEXT NOT NULL,
                    permanent INTEGER NOT NULL,
                    safe_actions_only INTEGER NOT NULL,
                    requires_human_approval_for_code INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS hermes_skills (
                    name TEXT PRIMARY KEY,
                    version TEXT NOT NULL,
                    description TEXT NOT NULL,
                    path TEXT NOT NULL,
                    permissions_json TEXT NOT NULL,
                    validations_json TEXT NOT NULL,
                    exists_on_disk INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS hermes_goals (
                    goal_id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    checkpoint TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    last_activity_at TEXT NOT NULL,
                    iteration_limit INTEGER NOT NULL,
                    time_limit_seconds INTEGER NOT NULL,
                    token_budget INTEGER NOT NULL,
                    completion_criteria TEXT NOT NULL,
                    failure_criteria TEXT NOT NULL,
                    next_step TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS hermes_memory (
                    scope TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (scope, memory_key)
                );

                CREATE TABLE IF NOT EXISTS hermes_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS hermes_runtime_cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    operational_state TEXT NOT NULL,
                    report_json TEXT NOT NULL
                );
                """
            )
        return self.path.exists() and self.path.is_file()

    def record_event(self, event: OdinEvent) -> None:
        safe_payload = event.to_dict()["payload"]
        with self._managed_connection() as conn:
            conn.execute(
                """
                INSERT INTO events (
                    timestamp, run_id, corr_id, component, event, severity, mode,
                    symbol, safe_to_trade, reason, payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.timestamp,
                    event.run_id,
                    event.corr_id,
                    event.component,
                    event.event,
                    event.severity,
                    event.mode,
                    event.symbol,
                    int(event.safe_to_trade),
                    event.reason,
                    json.dumps(safe_payload, sort_keys=True),
                ),
            )

    def set_state(self, key: str, value: str) -> None:
        updated_at = datetime.now(UTC).isoformat(timespec="seconds")
        with self._managed_connection() as conn:
            conn.execute(
                """
                INSERT INTO system_state (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value, updated_at),
            )

    def record_validation(self, state: OdinState) -> None:
        timestamp = datetime.now(UTC).isoformat(timespec="seconds")
        with self._managed_connection() as conn:
            conn.execute(
                """
                INSERT INTO validations (
                    timestamp, status, mode, safe_to_trade, real_trading, risk_state,
                    hermes_mode, jsonl_logger_ready, sqlite_initialized
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    state.status,
                    state.mode.value,
                    int(state.safe_to_trade),
                    int(state.real_trading),
                    state.risk_state.value,
                    state.hermes_mode.value,
                    int(state.jsonl_logger_ready),
                    int(state.sqlite_initialized),
                ),
            )

    def register_agents(self, agents: list[dict[str, object]]) -> None:
        updated_at = datetime.now(UTC).isoformat(timespec="seconds")
        with self._managed_connection() as conn:
            conn.executemany(
                """
                INSERT INTO hermes_agents (
                    name, purpose, preferred_route, model_tier, allowed_actions_json,
                    permanent, safe_actions_only, requires_human_approval_for_code, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    purpose = excluded.purpose,
                    preferred_route = excluded.preferred_route,
                    model_tier = excluded.model_tier,
                    allowed_actions_json = excluded.allowed_actions_json,
                    permanent = excluded.permanent,
                    safe_actions_only = excluded.safe_actions_only,
                    requires_human_approval_for_code = excluded.requires_human_approval_for_code,
                    updated_at = excluded.updated_at
                """,
                [
                    (
                        str(agent["name"]),
                        str(agent["purpose"]),
                        str(agent["preferred_route"]),
                        str(agent["model_tier"]),
                        json.dumps(agent["allowed_actions"], sort_keys=True),
                        int(bool(agent["permanent"])),
                        int(bool(agent["safe_actions_only"])),
                        int(bool(agent["requires_human_approval_for_code"])),
                        updated_at,
                    )
                    for agent in agents
                ],
            )

    def register_skills(self, skills: list[dict[str, object]]) -> None:
        updated_at = datetime.now(UTC).isoformat(timespec="seconds")
        with self._managed_connection() as conn:
            conn.executemany(
                """
                INSERT INTO hermes_skills (
                    name, version, description, path, permissions_json, validations_json,
                    exists_on_disk, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    version = excluded.version,
                    description = excluded.description,
                    path = excluded.path,
                    permissions_json = excluded.permissions_json,
                    validations_json = excluded.validations_json,
                    exists_on_disk = excluded.exists_on_disk,
                    updated_at = excluded.updated_at
                """,
                [
                    (
                        str(skill["name"]),
                        str(skill["version"]),
                        str(skill["description"]),
                        str(skill["path"]),
                        json.dumps(skill["permissions"], sort_keys=True),
                        json.dumps(skill["validations"], sort_keys=True),
                        int(bool(skill["exists"])),
                        updated_at,
                    )
                    for skill in skills
                ],
            )

    def upsert_hermes_goal(self, goal: dict[str, object]) -> None:
        with self._managed_connection() as conn:
            conn.execute(
                """
                INSERT INTO hermes_goals (
                    goal_id, description, priority, status, agent, checkpoint,
                    started_at, last_activity_at, iteration_limit, time_limit_seconds,
                    token_budget, completion_criteria, failure_criteria, next_step
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(goal_id) DO UPDATE SET
                    description = excluded.description,
                    priority = excluded.priority,
                    status = excluded.status,
                    agent = excluded.agent,
                    checkpoint = excluded.checkpoint,
                    last_activity_at = excluded.last_activity_at,
                    iteration_limit = excluded.iteration_limit,
                    time_limit_seconds = excluded.time_limit_seconds,
                    token_budget = excluded.token_budget,
                    completion_criteria = excluded.completion_criteria,
                    failure_criteria = excluded.failure_criteria,
                    next_step = excluded.next_step
                """,
                (
                    str(goal["goal_id"]),
                    str(goal["description"]),
                    str(goal["priority"]),
                    str(goal["status"]),
                    str(goal["agent"]),
                    str(goal["checkpoint"]),
                    str(goal["started_at"]),
                    str(goal["last_activity_at"]),
                    int(goal["iteration_limit"]),
                    int(goal["time_limit_seconds"]),
                    int(goal["token_budget"]),
                    str(goal["completion_criteria"]),
                    str(goal["failure_criteria"]),
                    str(goal["next_step"]),
                ),
            )

    def upsert_hermes_memory(self, scope: str, key: str, value: dict[str, object]) -> None:
        updated_at = datetime.now(UTC).isoformat(timespec="seconds")
        with self._managed_connection() as conn:
            conn.execute(
                """
                INSERT INTO hermes_memory (scope, memory_key, value_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(scope, memory_key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (scope, key, json.dumps(value, sort_keys=True), updated_at),
            )

    def create_hermes_checkpoint(
        self,
        *,
        checkpoint_id: str,
        goal_id: str,
        summary: str,
        state: dict[str, object],
    ) -> None:
        created_at = datetime.now(UTC).isoformat(timespec="seconds")
        with self._managed_connection() as conn:
            conn.execute(
                """
                INSERT INTO hermes_checkpoints (checkpoint_id, goal_id, summary, state_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(checkpoint_id) DO UPDATE SET
                    summary = excluded.summary,
                    state_json = excluded.state_json,
                    created_at = excluded.created_at
                """,
                (checkpoint_id, goal_id, summary, json.dumps(state, sort_keys=True), created_at),
            )

    def record_hermes_runtime(self, report: dict[str, object]) -> None:
        timestamp = datetime.now(UTC).isoformat(timespec="seconds")
        with self._managed_connection() as conn:
            conn.execute(
                """
                INSERT INTO hermes_runtime_cycles (timestamp, status, operational_state, report_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    timestamp,
                    str(report.get("status", "UNKNOWN")),
                    str(report.get("operational_state", "UNKNOWN")),
                    json.dumps(report, sort_keys=True),
                ),
            )
