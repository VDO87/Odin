import tempfile
import unittest
from pathlib import Path

from odin.adapters.mt5.mock_bridge import mt5_bridge_status
from odin.contracts.mt5_bridge import loaded_secret_key, send_available_key
from odin.core.smoke import run_runtime_smoke


class A14MT5MockBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _status(self):
        return mt5_bridge_status(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def test_mt5_mock_bridge_returns_ok(self):
        self.assertEqual(self._status()["status"], "OK")

    def test_mt5_bridge_mode_mock_only(self):
        self.assertEqual(self._status()["bridge_mode"], "MOCK_ONLY")

    def test_mt5_bridge_provider_mock(self):
        self.assertEqual(self._status()["provider"], "mt5_mock")

    def test_mt5_bridge_connected_false(self):
        self.assertIs(self._status()["connected"], False)

    def test_mt5_bridge_terminal_detected_false(self):
        self.assertIs(self._status()["terminal_detected"], False)

    def test_mt5_bridge_account_connected_false(self):
        self.assertIs(self._status()["account_connected"], False)

    def test_mt5_bridge_login_required_false(self):
        self.assertIs(self._status()["login_required"], False)

    def test_mt5_bridge_credentials_loaded_false(self):
        self.assertIs(self._status()[loaded_secret_key()], False)

    def test_mt5_bridge_real_mt5_imported_false(self):
        self.assertIs(self._status()["real_mt5_imported"], False)

    def test_mt5_bridge_order_send_available_false(self):
        self.assertIs(self._status()[send_available_key()], False)

    def test_mt5_bridge_execution_allowed_false(self):
        self.assertIs(self._status()["execution_allowed"], False)

    def test_mt5_bridge_safe_to_trade_false(self):
        self.assertIs(self._status()["safe_to_trade"], False)

    def test_mt5_bridge_real_trading_false(self):
        self.assertIs(self._status()["real_trading"], False)

    def test_runtime_smoke_includes_mt5_bridge(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )
        module_names = {str(module["name"]) for module in report["modules"]}

        self.assertEqual(report["modules_count"], 11)
        self.assertIn("mt5-bridge", module_names)
        self.assertEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
