import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odin.dashboard.routes import DashboardRoutes
from odin.trading.shadow_cycle import run_shadow_observation


class ShadowObservationTests(unittest.TestCase):
    def test_fresh_inputs_persist_no_decision_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "cycle.json"
            mt5 = {"status":"CONNECTED_DEMO_READ_ONLY","fresh":True,"as_of":"now","age_seconds":1,"market":{"symbol":"EURUSD"}}
            public = {"status":"OK","fresh":True,"latest_content_hash":"hash"}
            with patch("odin.trading.shadow_cycle.read_demo_readonly_state", return_value=mt5), patch("odin.trading.shadow_cycle.public_observation_cache_status", return_value=public):
                result = run_shadow_observation(state_path=str(target))
                second = run_shadow_observation(state_path=str(target))
            self.assertEqual(result["status"], "OBSERVED_NO_DECISION")
            self.assertFalse(result["decision_generated"])
            self.assertTrue(second["idempotent_replay"])
            self.assertFalse(result["execution_allowed"])
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["status"], "OBSERVED_NO_DECISION")

    def test_stale_inputs_block_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("odin.trading.shadow_cycle.read_demo_readonly_state", return_value={"status":"BLOCKED","fresh":False}), patch("odin.trading.shadow_cycle.public_observation_cache_status", return_value={"status":"OK","fresh":True}):
                result = run_shadow_observation(state_path=str(Path(tmp) / "cycle.json"))
        self.assertEqual(result["status"], "BLOCKED_INPUTS")
        self.assertFalse(result["trade_proposal_generated"])

    def test_dashboard_route_is_read_only(self):
        with patch("odin.dashboard.routes.run_shadow_observation", return_value={"status":"OBSERVED_NO_DECISION","execution_allowed":False}):
            status, result = DashboardRoutes().serve("/trading/shadow-cycle")
        self.assertEqual(status, 200)
        self.assertFalse(result["execution_allowed"])


if __name__ == "__main__":
    unittest.main()
