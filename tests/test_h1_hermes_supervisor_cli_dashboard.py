import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes


class H1HermesSupervisorCliDashboardTests(unittest.TestCase):
    def test_cli_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "hermes-supervisor"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["component"], "hermes_supervisor")
        self.assertIs(result["safe_to_trade"], False)
        self.assertIs(result["real_trading"], False)
        self.assertIn(result["status"], {"OK", "DEGRADED"})

    def test_dashboard_returns_runtime_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/hermes/runtime")
        self.assertEqual(code, 200)
        self.assertEqual(payload["component"], "hermes_supervisor")
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)


if __name__ == "__main__":
    unittest.main()
