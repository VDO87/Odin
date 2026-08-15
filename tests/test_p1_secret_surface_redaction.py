import io
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from odin.contracts.events import OdinEvent
from odin.dashboard.routes import DashboardRoutes
from odin.hermes.service import generate_hermes_summary
from odin.logging.jsonl_logger import JsonlLogger
from odin.reporting.operational_report import write_operational_report
from odin.storage.sqlite_store import SQLiteStore


class SecretSurfaceRedactionTests(unittest.TestCase):
    def test_sentinel_values_do_not_reach_persisted_or_operator_surfaces(self):
        sentinels = ("p1-password-sentinel", "p1-token-sentinel", "p1-login-sentinel")
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "ODIN_MT5_PASSWORD": sentinels[0], "ODIN_MT5_LOGIN": sentinels[2],
            "ODIN_MT5_SERVER": "p1-server-sentinel",
        }, clear=False):
            root = Path(tmp)
            log_path, sqlite_path = root / "events.jsonl", root / "events.sqlite"
            event = OdinEvent.create(
                run_id="p1", component="p1.test", event="sentinel",
                payload={"message": f"wrapped:{sentinels[0]}", "token": sentinels[1], "safe": "kept"},
            )
            JsonlLogger(log_path).write(event)
            emitted_log = log_path.read_text(encoding="utf-8")
            store = SQLiteStore(sqlite_path)
            store.initialize()
            store.record_event(event)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(sentinels[0] + " malformed-log-line\n")

            routes = DashboardRoutes(log_path=str(log_path), sqlite_path=str(sqlite_path))
            _, api_payload = routes.serve("/logs/tail")
            summary = generate_hermes_summary(log_path=str(log_path), sqlite_path=str(sqlite_path))
            report = write_operational_report(output_dir=str(root / "reports"), log_path=str(log_path), sqlite_path=str(sqlite_path))
            console = io.StringIO()
            with redirect_stdout(console):
                print(json.dumps({"api": api_payload, "hermes": summary, "report": report["status"]}))

            sqlite_payloads = [row[0] for row in sqlite3.connect(sqlite_path).execute("SELECT payload_json FROM events")]
            surfaces = [
                emitted_log, *sqlite_payloads,
                json.dumps(api_payload), json.dumps(summary), Path(report["report_path"]).read_text(encoding="utf-8"),
                routes.tradedesk_html(), routes.cockpit_html(), console.getvalue(),
            ]
        for sentinel in sentinels:
            self.assertTrue(all(sentinel not in surface for surface in surfaces))
        self.assertIn("[REDACTED]", surfaces[0])
        self.assertIn("[REDACTED_UNPARSEABLE_LOG_LINE]", json.dumps(api_payload))


if __name__ == "__main__":
    unittest.main()
