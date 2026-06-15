import unittest

from odin.contracts.observation_frame import ObservationFrame, proposal_generated_key


class A19ObservationFrameContractTests(unittest.TestCase):
    def test_observation_frame_contract_serializes(self):
        frame = ObservationFrame(
            component="observation_frame",
            status="OK",
            frame_mode="OBSERVATION_ONLY",
            selected_source="mt5_feed_mock",
            fallback_source="market_data_mock",
            primary_symbol="EURUSD",
            source="mt5_mock",
            feed_quality_status="OK",
            data_quality_status="OK",
            strategy_status="READY_NO_DECISION",
            decision_intent_status="NO_DECISION",
            risk_status="BLOCKED",
            shadow_proposal_status="BLOCKED",
            safe_to_use_for_decision=False,
            decision_generated=False,
            proposal_generated=False,
            risk_approved=False,
            execution_allowed=False,
            safe_to_trade=False,
            real_trading=False,
            reason="observation_frame_mock_only",
            blockers=["decision_use_blocked"],
            notes=["contract test"],
        )

        payload = frame.to_dict()

        self.assertEqual(payload["component"], "observation_frame")
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["frame_mode"], "OBSERVATION_ONLY")
        self.assertEqual(payload["selected_source"], "mt5_feed_mock")
        self.assertEqual(payload["primary_symbol"], "EURUSD")
        self.assertEqual(payload["source"], "mt5_mock")
        self.assertEqual(payload["feed_quality_status"], "OK")
        self.assertEqual(payload["data_quality_status"], "OK")
        self.assertEqual(payload["strategy_status"], "READY_NO_DECISION")
        self.assertEqual(payload["decision_intent_status"], "NO_DECISION")
        self.assertEqual(payload["risk_status"], "BLOCKED")
        self.assertEqual(payload["shadow_proposal_status"], "BLOCKED")
        self.assertIs(payload["safe_to_use_for_decision"], False)
        self.assertIs(payload["decision_generated"], False)
        self.assertIs(payload[proposal_generated_key()], False)
        self.assertIs(payload["risk_approved"], False)
        self.assertIs(payload["execution_allowed"], False)
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)


if __name__ == "__main__":
    unittest.main()
