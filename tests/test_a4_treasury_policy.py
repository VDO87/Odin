import unittest

from odin.treasury.policy import can_mark_safe_to_transfer, default_block_reasons
from odin.treasury.state import default_treasury_state


class A4TreasuryPolicyTests(unittest.TestCase):
    def test_transfer_block_reasons_present(self):
        reasons = default_block_reasons()

        self.assertIn("treasury_skeleton_read_only", reasons)
        self.assertIn("no_real_broker_data", reasons)
        self.assertIn("tax_reserve_not_validated", reasons)
        self.assertIn("protected_capital_policy_not_funded", reasons)

    def test_default_jurisdiction_is_pt(self):
        state = default_treasury_state()

        self.assertEqual(state.jurisdiction, "PT")

    def test_default_fiscal_residency_is_pt(self):
        state = default_treasury_state()

        self.assertEqual(state.fiscal_residency, "PT")

    def test_read_only_policy_keeps_transfer_blocked(self):
        self.assertIs(can_mark_safe_to_transfer(read_only=True, block_reasons=[]), False)


if __name__ == "__main__":
    unittest.main()

