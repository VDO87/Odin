import unittest

from odin.contracts.observation_frame_quality import (
    ObservationFrameQualityGate,
    ObservationFrameQualityReport,
    proposal_generated_key,
)


class A20ObservationFrameQualityContractTests(unittest.TestCase):
    def test_observation_frame_quality_gate_serializes(self):
        gate = ObservationFrameQualityGate(
            gate_name="frame_present",
            passed=True,
            status="PASS",
            blocking=True,
            reason="gate_passed",
            details={"present": True},
        )

        payload = gate.to_dict()

        self.assertEqual(payload["gate_name"], "frame_present")
        self.assertIs(payload["passed"], True)
        self.assertEqual(payload["status"], "PASS")
        self.assertIs(payload["blocking"], True)
        self.assertEqual(payload["reason"], "gate_passed")
        self.assertEqual(payload["details"], {"present": True})

    def test_observation_frame_quality_report_serializes(self):
        gate = ObservationFrameQualityGate(
            gate_name="frame_present",
            passed=True,
            status="PASS",
            blocking=True,
            reason="gate_passed",
        )
        report = ObservationFrameQualityReport(
            component="observation_frame_quality",
            status="OK",
            quality_mode="OBSERVATION_FRAME_GATES",
            frame_quality_status="OK",
            selected_source="mt5_feed_mock",
            primary_symbol="EURUSD",
            feed_quality_status="OK",
            data_quality_status="OK",
            strategy_status="READY_NO_DECISION",
            decision_intent_status="NO_DECISION",
            risk_status="BLOCKED",
            shadow_proposal_status="BLOCKED",
            gates_count=1,
            all_gates_passed=True,
            safe_to_use_for_decision=False,
            decision_generated=False,
            proposal_generated=False,
            risk_approved=False,
            execution_allowed=False,
            safe_to_trade=False,
            real_trading=False,
            reason="observation_frame_quality_mock_passed",
            gates=[gate],
            blockers=["decision_use_blocked"],
            notes=["contract test"],
        )

        payload = report.to_dict()

        self.assertEqual(payload["component"], "observation_frame_quality")
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["quality_mode"], "OBSERVATION_FRAME_GATES")
        self.assertEqual(payload["frame_quality_status"], "OK")
        self.assertEqual(payload["selected_source"], "mt5_feed_mock")
        self.assertEqual(payload["primary_symbol"], "EURUSD")
        self.assertEqual(payload["feed_quality_status"], "OK")
        self.assertEqual(payload["data_quality_status"], "OK")
        self.assertEqual(payload["strategy_status"], "READY_NO_DECISION")
        self.assertEqual(payload["decision_intent_status"], "NO_DECISION")
        self.assertEqual(payload["risk_status"], "BLOCKED")
        self.assertEqual(payload["shadow_proposal_status"], "BLOCKED")
        self.assertEqual(payload["gates_count"], 1)
        self.assertIs(payload["all_gates_passed"], True)
        self.assertIs(payload["safe_to_use_for_decision"], False)
        self.assertIs(payload["decision_generated"], False)
        self.assertIs(payload[proposal_generated_key()], False)
        self.assertIs(payload["risk_approved"], False)
        self.assertIs(payload["execution_allowed"], False)
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)
        self.assertEqual(payload["gates"][0]["gate_name"], "frame_present")


if __name__ == "__main__":
    unittest.main()
