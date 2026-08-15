import unittest
from pathlib import Path


class MT5ReadOnlyInspectorContractTests(unittest.TestCase):
    def test_script_has_only_observational_mt5_calls_and_no_secret_contract(self):
        script = (Path(__file__).parents[1] / "scripts" / "windows" / "Inspect-ODIN-MT5-ReadOnly.ps1").read_text(encoding="utf-8").lower()
        for allowed in ("mt5.initialize", "mt5.last_error", "mt5.terminal_info", "mt5.account_info", "mt5.symbol_info", "mt5.copy_rates_range", "mt5.copy_ticks_range", "mt5.shutdown"):
            with self.subTest(allowed=allowed):
                self.assertIn(allowed, script)
        for forbidden in ("order_send", "mt5.login", "password", "odin_mt5_login", "odin_mt5_password", "positions_get", "symbol_select"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, script)

    def test_runbook_keeps_hermes_read_only_and_documents_gap_classes(self):
        runbook = (Path(__file__).parents[1] / "docs" / "runbooks" / "MT5_READONLY_ODIN_HERMES.md").read_text(encoding="utf-8")
        for phrase in ("EXPECTED_GAP", "NO_TICK_GAP", "SUSPICIOUS_GAP", "INVALID_GAP", "Hermes pode ler e resumir"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, runbook)


if __name__ == "__main__":
    unittest.main()
