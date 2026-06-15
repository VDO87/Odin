import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.core.bootstrap import validate_runtime
from odin.dashboard.routes import DashboardRoutes
from odin.hermes.service import generate_hermes_summary


class A3HermesSummaryTests(unittest.TestCase):
    def _summary(self) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            validate_runtime(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            return generate_hermes_summary(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

    def test_hermes_summary_returns_ok(self):
        summary = self._summary()

        self.assertEqual(summary["status"], "OK")
        self.assertEqual(summary["component"], "hermes")
        self.assertIn("summary", summary)

    def test_hermes_summary_is_read_only(self):
        summary = self._summary()

        self.assertIs(summary["read_only"], True)
        self.assertEqual(summary["hermes_mode"], "READ_ONLY")

    def test_hermes_summary_keeps_safe_to_trade_false(self):
        summary = self._summary()

        self.assertIs(summary["safe_to_trade"], False)

    def test_hermes_summary_keeps_real_trading_false(self):
        summary = self._summary()

        self.assertIs(summary["real_trading"], False)

    def test_cli_hermes_summary_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "hermes-summary"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        summary = json.loads(completed.stdout)
        self.assertEqual(summary["status"], "OK")
        self.assertIs(summary["read_only"], True)
        self.assertIs(summary["safe_to_trade"], False)
        self.assertIs(summary["real_trading"], False)

    def test_dashboard_hermes_summary_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            status, payload = routes.serve("/hermes/summary")

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["component"], "hermes")
        self.assertIs(payload["read_only"], True)


if __name__ == "__main__":
    unittest.main()

