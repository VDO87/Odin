"""SQLite storage for A1 audit state."""

from __future__ import annotations

import json
import sqlite3
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

    def initialize(self) -> bool:
        with self.connect() as conn:
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
                """
            )
        return self.path.exists() and self.path.is_file()

    def record_event(self, event: OdinEvent) -> None:
        with self.connect() as conn:
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
                    json.dumps(event.payload, sort_keys=True),
                ),
            )

    def set_state(self, key: str, value: str) -> None:
        updated_at = datetime.now(UTC).isoformat(timespec="seconds")
        with self.connect() as conn:
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
        with self.connect() as conn:
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

