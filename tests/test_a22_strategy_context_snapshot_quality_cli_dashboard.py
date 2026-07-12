import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes


class A22StrategyContextSnapshotQualityCliDashboardTests(unittest.TestCase):
    def test_cli_returns_read_only_quality_report(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "strategy-context-snapshot-quality"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["component"], "strategy_context_snapshot_quality")
        self.assertIs(result["execution_allowed"], False)
        self.assertIs(result["safe_to_use_for_decision"], False)

    def test_dashboard_returns_read_only_quality_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/strategy/context/snapshot/quality")
        self.assertEqual(code, 200)
        self.assertEqual(payload["component"], "strategy_context_snapshot_quality")
        self.assertEqual(payload["primary_symbol"], "EURUSD")
        self.assertIs(payload["safe_to_trade"], False)


if __name__ == "__main__":
    unittest.main()
