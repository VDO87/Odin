import tempfile
import unittest
from pathlib import Path

from odin.contracts.observation_frame import proposal_generated_key
from odin.core.smoke import run_runtime_smoke
from odin.decision.observation_frame import observation_frame_status


class A19ObservationFrameTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _status(self):
        return observation_frame_status(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def test_observation_frame_returns_ok(self):
        self.assertEqual(self._status()["status"], "OK")

    def test_observation_frame_mode_observation_only(self):
        self.assertEqual(self._status()["frame_mode"], "OBSERVATION_ONLY")

    def test_observation_frame_selected_source_mt5_feed_mock(self):
        self.assertEqual(self._status()["selected_source"], "mt5_feed_mock")

    def test_observation_frame_primary_symbol_eurusd(self):
        self.assertEqual(self._status()["primary_symbol"], "EURUSD")

    def test_observation_frame_reads_feed_quality_status(self):
        self.assertEqual(self._status()["feed_quality_status"], "OK")

    def test_observation_frame_reads_data_quality_status(self):
        self.assertEqual(self._status()["data_quality_status"], "OK")

    def test_observation_frame_reads_strategy_status(self):
        self.assertEqual(self._status()["strategy_status"], "READY_NO_DECISION")

    def test_observation_frame_reads_decision_intent_status(self):
        self.assertEqual(self._status()["decision_intent_status"], "NO_DECISION")

    def test_observation_frame_reads_risk_status(self):
        self.assertEqual(self._status()["risk_status"], "BLOCKED")

    def test_observation_frame_reads_shadow_proposal_status(self):
        self.assertEqual(self._status()["shadow_proposal_status"], "BLOCKED")

    def test_observation_frame_safe_to_use_for_decision_false(self):
        self.assertIs(self._status()["safe_to_use_for_decision"], False)

    def test_observation_frame_decision_generated_false(self):
        self.assertIs(self._status()["decision_generated"], False)

    def test_observation_frame_trade_proposal_generated_false(self):
        self.assertIs(self._status()[proposal_generated_key()], False)

    def test_observation_frame_risk_approved_false(self):
        self.assertIs(self._status()["risk_approved"], False)

    def test_observation_frame_execution_allowed_false(self):
        self.assertIs(self._status()["execution_allowed"], False)

    def test_observation_frame_safe_to_trade_false(self):
        self.assertIs(self._status()["safe_to_trade"], False)

    def test_observation_frame_real_trading_false(self):
        self.assertIs(self._status()["real_trading"], False)

    def test_observation_frame_includes_required_blockers(self):
        blockers = set(self._status()["blockers"])

        self.assertIn("decision_use_blocked", blockers)
        self.assertIn("risk_gate_blocked", blockers)
        self.assertIn("shadow_proposal_blocked", blockers)
        self.assertIn("execution_disabled", blockers)
        self.assertIn("real_trading_disabled", blockers)

    def test_smoke_includes_observation_frame(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )
        names = {str(module["name"]) for module in report["modules"]}

        self.assertIn("observation-frame", names)
        self.assertEqual(report["status"], "PASS")

    def test_smoke_modules_count_19(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

        self.assertEqual(report["modules_count"], 20)


if __name__ == "__main__":
    unittest.main()
