import unittest

from odin.adapters.mt5.demo_guard import demo_account_guard


class MT5DemoGuardTests(unittest.TestCase):
    def test_demo_is_prepared_but_never_unlocked(self):
        result = demo_account_guard("demo")

        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertIs(result["account_mode_accepted"], True)
        self.assertIs(result["terminal_connection_attempted"], False)
        self.assertIs(result["execution_allowed"], False)
        self.assertIs(result["safe_to_trade"], False)
        self.assertIs(result["real_trading"], False)

    def test_missing_real_and_unknown_modes_fail_closed(self):
        for value, reason in ((None, "demo_account_required"), ("real", "real_account_mode_rejected"), ("test", "unknown_account_mode_rejected")):
            with self.subTest(value=value):
                result = demo_account_guard(value)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["reason"], reason)
                self.assertIs(result["execution_allowed"], False)


if __name__ == "__main__":
    unittest.main()
