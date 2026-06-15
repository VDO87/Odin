import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.core.market_watch import run_market_watch
from odin.dashboard.routes import DashboardRoutes


class A7DataQualityCliDashboardTests(unittest.TestCase):
    def test_cli_data_quality_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "data-quality"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "OK")
        self.assertEqual(report["source"], "mock")
        self.assertEqual(report["gates_count"], 11)
        self.assertIs(report["safe_to_use_for_decision"], False)

    def test_dashboard_data_quality_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/data/quality")

        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["component"], "data_quality")
        self.assertEqual(payload["gates_count"], 11)

    def test_market_watch_includes_data_quality_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = run_market_watch(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

        self.assertEqual(status["data_quality_status"], "OK")
        self.assertEqual(status["data_quality_blocking_reasons"], [])
        self.assertIs(status["safe_to_use_for_decision"], False)


if __name__ == "__main__":
    unittest.main()

