import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes


class A9DecisionCliDashboardTests(unittest.TestCase):
    def test_cli_decision_intent_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "decision-intent"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        intent = json.loads(completed.stdout)
        self.assertEqual(intent["status"], "OK")
        self.assertEqual(intent["component"], "decision_intent")
        self.assertEqual(intent["decision_intent_status"], "NO_DECISION")
        self.assertIs(intent["risk_approved"], False)

    def test_dashboard_decision_intent_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/decision/intent")

        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["component"], "decision_intent")
        self.assertEqual(payload["decision_intent_mode"], "INTENT_SKELETON")
        self.assertIs(payload["execution_allowed"], False)


if __name__ == "__main__":
    unittest.main()
