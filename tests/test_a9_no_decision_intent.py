import tempfile
import unittest
from pathlib import Path

from odin.decision.intent import decision_intent


class A9NoDecisionIntentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _intent(self):
        return decision_intent(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def test_no_decision_intent_returns_ok(self):
        self.assertEqual(self._intent()["status"], "OK")

    def test_decision_intent_status_no_decision(self):
        self.assertEqual(self._intent()["decision_intent_status"], "NO_DECISION")

    def test_decision_intent_mode_skeleton(self):
        self.assertEqual(self._intent()["decision_intent_mode"], "INTENT_SKELETON")

    def test_decision_intent_keeps_safe_to_trade_false(self):
        self.assertIs(self._intent()["safe_to_trade"], False)

    def test_decision_intent_keeps_real_trading_false(self):
        self.assertIs(self._intent()["real_trading"], False)

    def test_decision_intent_execution_allowed_false(self):
        self.assertIs(self._intent()["execution_allowed"], False)

    def test_decision_generated_false(self):
        self.assertIs(self._intent()["decision_generated"], False)

    def test_trade_proposal_generated_false(self):
        self.assertIs(self._intent()["trade_proposal_generated"], False)

    def test_risk_approved_false(self):
        self.assertIs(self._intent()["risk_approved"], False)

    def test_decision_intent_reads_strategy_status(self):
        self.assertEqual(self._intent()["strategy_status"], "READY_NO_DECISION")

    def test_decision_intent_reads_data_quality_status(self):
        self.assertEqual(self._intent()["data_quality_status"], "OK")

    def test_decision_intent_includes_required_blockers(self):
        blockers = self._intent()["blockers"]

        self.assertIn("strategy_observe_only", blockers)
        self.assertIn("risk_engine_ready_blocking", blockers)
        self.assertIn("real_trading_disabled", blockers)
        self.assertIn("execution_disabled", blockers)


if __name__ == "__main__":
    unittest.main()
