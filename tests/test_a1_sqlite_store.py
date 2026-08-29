from concurrent.futures import ThreadPoolExecutor
import sqlite3
import tempfile
import unittest
from pathlib import Path

from odin.core.bootstrap import validate_runtime
from odin.contracts.events import OdinEvent
from odin.storage.sqlite_store import SQLiteStore


class A1SQLiteStoreTests(unittest.TestCase):
    def test_sqlite_initializes_required_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "runtime" / "odin.sqlite"
            store = SQLiteStore(db_path)

            self.assertIs(store.initialize(), True)

            with sqlite3.connect(db_path) as conn:
                tables = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }

        self.assertTrue({"system_state", "events", "validations"}.issubset(tables))

    def test_validate_records_event_and_validation_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "runtime" / "odin.sqlite"
            result = validate_runtime(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(db_path),
            )

            self.assertEqual(result["status"], "PASS")

            with sqlite3.connect(db_path) as conn:
                event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                validation = conn.execute(
                    """
                    SELECT status, mode, safe_to_trade, real_trading, risk_state, hermes_mode,
                           jsonl_logger_ready, sqlite_initialized
                    FROM validations
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ).fetchone()

        self.assertGreaterEqual(event_count, 1)
        self.assertEqual(
            validation,
            ("PASS", "OFF_SAFE", 0, 0, "READY_BLOCKING", "READ_ONLY", 1, 1),
        )

    def test_concurrent_store_instances_share_one_bounded_writer_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "runtime" / "odin.sqlite"
            SQLiteStore(db_path).initialize()
            events = [
                OdinEvent.create(
                    run_id=f"concurrent-{index}",
                    component="test.sqlite",
                    event="test.concurrent_write",
                    payload={"index": index},
                )
                for index in range(64)
            ]

            def write(event: OdinEvent) -> None:
                SQLiteStore(db_path).record_event(event)

            with ThreadPoolExecutor(max_workers=16) as executor:
                list(executor.map(write, events))

            with sqlite3.connect(db_path) as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM events WHERE event = 'test.concurrent_write'"
                ).fetchone()[0]
                journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

        self.assertEqual(count, 64)
        self.assertEqual(journal_mode, "wal")


if __name__ == "__main__":
    unittest.main()
