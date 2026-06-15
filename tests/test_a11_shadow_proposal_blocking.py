import tempfile
import unittest
from pathlib import Path

from odin.decision.shadow_proposal import shadow_proposal


class A11ShadowProposalBlockingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _proposal(self):
        return shadow_proposal(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def test_shadow_proposal_returns_ok(self):
        self.assertEqual(self._proposal()["status"], "OK")

    def test_shadow_proposal_status_blocked(self):
        self.assertEqual(self._proposal()["shadow_proposal_status"], "BLOCKED")

    def test_shadow_mode_skeleton(self):
        self.assertEqual(self._proposal()["shadow_mode"], "SHADOW_SKELETON")

    def test_shadow_only_true(self):
        self.assertIs(self._proposal()["shadow_only"], True)

    def test_shadow_proposal_keeps_safe_to_trade_false(self):
        self.assertIs(self._proposal()["safe_to_trade"], False)

    def test_shadow_proposal_keeps_real_trading_false(self):
        self.assertIs(self._proposal()["real_trading"], False)

    def test_shadow_proposal_execution_allowed_false(self):
        self.assertIs(self._proposal()["execution_allowed"], False)

    def test_risk_approved_false(self):
        self.assertIs(self._proposal()["risk_approved"], False)

    def test_decision_generated_false(self):
        self.assertIs(self._proposal()["decision_generated"], False)

    def test_trade_proposal_generated_false(self):
        self.assertIs(self._proposal()["trade_proposal_generated"], False)

    def test_shadow_proposal_reads_risk_gate_status(self):
        self.assertEqual(self._proposal()["risk_status"], "BLOCKED")

    def test_shadow_proposal_reads_decision_intent_status(self):
        self.assertEqual(self._proposal()["decision_intent_status"], "NO_DECISION")

    def test_shadow_proposal_reads_strategy_status(self):
        self.assertEqual(self._proposal()["strategy_status"], "READY_NO_DECISION")

    def test_shadow_proposal_reads_data_quality_status(self):
        self.assertEqual(self._proposal()["data_quality_status"], "OK")

    def test_shadow_proposal_includes_required_blockers(self):
        blockers = self._proposal()["blockers"]

        self.assertIn("risk_gate_blocked", blockers)
        self.assertIn("no_decision_intent", blockers)
        self.assertIn("strategy_observe_only", blockers)
        self.assertIn("real_trading_disabled", blockers)
        self.assertIn("execution_disabled", blockers)


if __name__ == "__main__":
    unittest.main()
