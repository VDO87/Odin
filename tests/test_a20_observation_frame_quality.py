import tempfile
import unittest
from pathlib import Path

from odin.core.smoke import run_runtime_smoke
from odin.decision.observation_frame_quality import observation_frame_quality_status


class A20ObservationFrameQualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _status(self):
        return observation_frame_quality_status(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def test_observation_frame_quality_returns_ok(self):
        self.assertEqual(self._status()["status"], "OK")

    def test_observation_frame_quality_mode_gates(self):
        self.assertEqual(self._status()["quality_mode"], "OBSERVATION_FRAME_GATES")

    def test_observation_frame_quality_status_ok(self):
        self.assertEqual(self._status()["frame_quality_status"], "OK")

    def test_observation_frame_quality_selected_source_mt5_feed_mock(self):
        self.assertEqual(self._status()["selected_source"], "mt5_feed_mock")

    def test_observation_frame_quality_primary_symbol_eurusd(self):
        self.assertEqual(self._status()["primary_symbol"], "EURUSD")

    def test_observation_frame_quality_reads_feed_quality_status(self):
        self.assertEqual(self._status()["feed_quality_status"], "OK")

    def test_observation_frame_quality_reads_data_quality_status(self):
        self.assertEqual(self._status()["data_quality_status"], "OK")

    def test_observation_frame_quality_reads_strategy_status(self):
        self.assertEqual(self._status()["strategy_status"], "READY_NO_DECISION")

    def test_observation_frame_quality_reads_decision_intent_status(self):
        self.assertEqual(self._status()["decision_intent_status"], "NO_DECISION")

    def test_observation_frame_quality_reads_risk_status(self):
        self.assertEqual(self._status()["risk_status"], "BLOCKED")

    def test_observation_frame_quality_reads_shadow_proposal_status(self):
        self.assertEqual(self._status()["shadow_proposal_status"], "BLOCKED")

    def test_observation_frame_quality_gates_count_at_least_12(self):
        self.assertGreaterEqual(self._status()["gates_count"], 12)

    def test_observation_frame_quality_all_gates_passed_true(self):
        self.assertIs(self._status()["all_gates_passed"], True)

    def test_observation_frame_quality_safe_to_use_for_decision_false(self):
        self.assertIs(self._status()["safe_to_use_for_decision"], False)

    def test_observation_frame_quality_decision_generated_false(self):
        self.assertIs(self._status()["decision_generated"], False)

    def test_observation_frame_quality_trade_proposal_generated_false(self):
        self.assertIs(self._status()["trade_proposal_generated"], False)

    def test_observation_frame_quality_risk_approved_false(self):
        self.assertIs(self._status()["risk_approved"], False)

    def test_observation_frame_quality_execution_allowed_false(self):
        self.assertIs(self._status()["execution_allowed"], False)

    def test_observation_frame_quality_safe_to_trade_false(self):
        self.assertIs(self._status()["safe_to_trade"], False)

    def test_observation_frame_quality_real_trading_false(self):
        self.assertIs(self._status()["real_trading"], False)

    def test_observation_frame_quality_includes_required_blockers(self):
        blockers = set(self._status()["blockers"])

        self.assertIn("decision_use_blocked", blockers)
        self.assertIn("risk_gate_blocked", blockers)
        self.assertIn("shadow_proposal_blocked", blockers)
        self.assertIn("execution_disabled", blockers)
        self.assertIn("real_trading_disabled", blockers)

    def test_smoke_includes_observation_frame_quality(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )
        names = {str(module["name"]) for module in report["modules"]}

        self.assertIn("observation-frame-quality", names)
        self.assertEqual(report["status"], "PASS")

    def test_smoke_modules_count_19(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

        self.assertEqual(report["modules_count"], 21)


if __name__ == "__main__":
    unittest.main()
