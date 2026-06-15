import unittest

from odin.treasury.portugal_tax import portugal_tax_policy, tax_reserve_required


class A4TreasuryPortugalTaxTests(unittest.TestCase):
    def test_portugal_tax_rates_are_configured(self):
        policy = portugal_tax_policy()

        self.assertEqual(policy.capital_gains_reserve_rate, 0.30)
        self.assertEqual(policy.capital_income_reserve_rate, 0.30)
        self.assertEqual(policy.short_holding_high_income_reserve_rate, 0.53)
        self.assertIs(policy.only_realized_profit_counts, True)
        self.assertIs(policy.release_excess_only_after_irs_closed, True)

    def test_tax_reserve_zero_when_no_realized_profit(self):
        self.assertEqual(tax_reserve_required(0.0), 0.0)
        self.assertEqual(tax_reserve_required(-10.0), 0.0)


if __name__ == "__main__":
    unittest.main()

