import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes


class A10RiskGateCliDashboardTests(unittest.TestCase):
    def test_cli_risk_gate_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "risk-gate"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["component"], "risk_gate")
        self.assertEqual(result["risk_status"], "BLOCKED")
        self.assertIs(result["risk_approved"], False)

    def test_dashboard_risk_gate_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/risk/gate")

        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["component"], "risk_gate")
        self.assertEqual(payload["risk_gate_mode"], "BLOCKING_SKELETON")
        self.assertIs(payload["execution_allowed"], False)


if __name__ == "__main__":
    unittest.main()
