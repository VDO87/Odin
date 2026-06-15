import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes


class A14MT5BridgeCliDashboardTests(unittest.TestCase):
    def test_cli_mt5_bridge_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "mt5-bridge"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["component"], "mt5_bridge")
        self.assertEqual(result["bridge_mode"], "MOCK_ONLY")
        self.assertIs(result["execution_allowed"], False)

    def test_dashboard_mt5_bridge_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/mt5/bridge")

        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["component"], "mt5_bridge")
        self.assertEqual(payload["provider"], "mt5_mock")
        self.assertIs(payload["safe_to_trade"], False)


if __name__ == "__main__":
    unittest.main()
