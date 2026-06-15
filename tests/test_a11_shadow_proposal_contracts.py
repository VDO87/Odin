import unittest

from odin.contracts.shadow_proposal import ShadowProposal


class A11ShadowProposalContractTests(unittest.TestCase):
    def test_shadow_proposal_contract_serializes(self):
        proposal = ShadowProposal(
            component="shadow_proposal",
            status="OK",
            shadow_proposal_status="BLOCKED",
            shadow_mode="SHADOW_SKELETON",
            shadow_only=True,
            symbol="EURUSD",
            source="mock",
            decision_intent_status="NO_DECISION",
            risk_status="BLOCKED",
            risk_approved=False,
            strategy_status="READY_NO_DECISION",
            data_quality_status="OK",
            read_only=True,
            safe_to_trade=False,
            real_trading=False,
            execution_allowed=False,
            decision_generated=False,
            proposal_generated=False,
            reason="shadow_proposal_skeleton_blocked",
            blockers=["risk_gate_blocked"],
            notes=["contract test"],
        )

        payload = proposal.to_dict()

        self.assertEqual(payload["component"], "shadow_proposal")
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["shadow_proposal_status"], "BLOCKED")
        self.assertEqual(payload["shadow_mode"], "SHADOW_SKELETON")
        self.assertIs(payload["shadow_only"], True)
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)
        self.assertIs(payload["execution_allowed"], False)


if __name__ == "__main__":
    unittest.main()
