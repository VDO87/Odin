import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes


class A8StrategyCliDashboardTests(unittest.TestCase):
    def test_cli_strategy_status_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "strategy-status"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        status = json.loads(completed.stdout)
        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["strategy_status"], "READY_NO_DECISION")
        self.assertIs(status["decision_generated"], False)
        self.assertIs(status["trade_proposal_generated"], False)

    def test_dashboard_strategy_status_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/strategy/status")

        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["component"], "strategy")
        self.assertEqual(payload["strategy_mode"], "OBSERVE_ONLY")
        self.assertIs(payload["execution_allowed"], False)


if __name__ == "__main__":
    unittest.main()

