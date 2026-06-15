import tempfile
import unittest
from pathlib import Path

from odin.risk.gate import risk_gate


class A10RiskGateBlockingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _gate(self):
        return risk_gate(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def test_risk_gate_returns_ok(self):
        self.assertEqual(self._gate()["status"], "OK")

    def test_risk_gate_status_blocked(self):
        self.assertEqual(self._gate()["risk_status"], "BLOCKED")

    def test_risk_gate_mode_blocking_skeleton(self):
        self.assertEqual(self._gate()["risk_gate_mode"], "BLOCKING_SKELETON")

    def test_risk_gate_keeps_safe_to_trade_false(self):
        self.assertIs(self._gate()["safe_to_trade"], False)

    def test_risk_gate_keeps_real_trading_false(self):
        self.assertIs(self._gate()["real_trading"], False)

    def test_risk_gate_execution_allowed_false(self):
        self.assertIs(self._gate()["execution_allowed"], False)

    def test_risk_approved_false(self):
        self.assertIs(self._gate()["risk_approved"], False)

    def test_decision_generated_false(self):
        self.assertIs(self._gate()["decision_generated"], False)

    def test_trade_proposal_generated_false(self):
        self.assertIs(self._gate()["trade_proposal_generated"], False)

    def test_risk_gate_reads_decision_intent_status(self):
        self.assertEqual(self._gate()["decision_intent_status"], "NO_DECISION")

    def test_risk_gate_reads_strategy_status(self):
        self.assertEqual(self._gate()["strategy_status"], "READY_NO_DECISION")

    def test_risk_gate_reads_data_quality_status(self):
        self.assertEqual(self._gate()["data_quality_status"], "OK")

    def test_risk_gate_includes_required_blockers(self):
        blockers = self._gate()["blockers"]

        self.assertIn("no_decision_intent", blockers)
        self.assertIn("strategy_observe_only", blockers)
        self.assertIn("risk_gate_skeleton", blockers)
        self.assertIn("real_trading_disabled", blockers)
        self.assertIn("execution_disabled", blockers)


if __name__ == "__main__":
    unittest.main()
