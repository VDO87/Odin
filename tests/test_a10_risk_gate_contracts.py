import unittest

from odin.contracts.risk_gate import RiskGateResult


class A10RiskGateContractTests(unittest.TestCase):
    def test_risk_gate_contract_serializes(self):
        result = RiskGateResult(
            component="risk_gate",
            status="OK",
            risk_status="BLOCKED",
            risk_gate_mode="BLOCKING_SKELETON",
            symbol="EURUSD",
            source="mock",
            decision_intent_status="NO_DECISION",
            decision_intent_mode="INTENT_SKELETON",
            strategy_status="READY_NO_DECISION",
            data_quality_status="OK",
            read_only=True,
            safe_to_trade=False,
            real_trading=False,
            execution_allowed=False,
            decision_generated=False,
            proposal_generated=False,
            risk_approved=False,
            reason="risk_gate_skeleton_blocks_all",
            blockers=["risk_gate_skeleton"],
            notes=["contract test"],
        )

        payload = result.to_dict()

        self.assertEqual(payload["component"], "risk_gate")
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["risk_status"], "BLOCKED")
        self.assertEqual(payload["risk_gate_mode"], "BLOCKING_SKELETON")
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)
        self.assertIs(payload["execution_allowed"], False)
        self.assertIs(payload["risk_approved"], False)


if __name__ == "__main__":
    unittest.main()
