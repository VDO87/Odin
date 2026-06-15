import unittest

from odin.contracts.decision_intent import DecisionIntent


class A9DecisionIntentContractTests(unittest.TestCase):
    def test_decision_intent_contract_serializes(self):
        intent = DecisionIntent(
            component="decision_intent",
            status="OK",
            decision_intent_status="NO_DECISION",
            decision_intent_mode="INTENT_SKELETON",
            symbol="EURUSD",
            source="mock",
            strategy_name="baseline_observer",
            strategy_status="READY_NO_DECISION",
            data_quality_status="OK",
            read_only=True,
            safe_to_trade=False,
            real_trading=False,
            execution_allowed=False,
            decision_generated=False,
            proposal_generated=False,
            risk_approved=False,
            reason="decision_intent_skeleton_blocked",
            blockers=["strategy_observe_only"],
            notes=["contract test"],
        )

        payload = intent.to_dict()

        self.assertEqual(payload["component"], "decision_intent")
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["decision_intent_status"], "NO_DECISION")
        self.assertEqual(payload["decision_intent_mode"], "INTENT_SKELETON")
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)
        self.assertIs(payload["execution_allowed"], False)
        self.assertIs(payload["risk_approved"], False)


if __name__ == "__main__":
    unittest.main()
