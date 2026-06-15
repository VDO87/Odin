import sqlite3
import tempfile
import unittest
from pathlib import Path

from odin.core.bootstrap import validate_runtime
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


if __name__ == "__main__":
    unittest.main()
