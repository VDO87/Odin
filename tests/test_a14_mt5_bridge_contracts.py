import unittest

from odin.contracts.mt5_bridge import MT5BridgeStatus, loaded_secret_key, send_available_key


class A14MT5BridgeContractTests(unittest.TestCase):
    def test_mt5_bridge_contract_serializes(self):
        result = MT5BridgeStatus(
            component="mt5_bridge",
            status="OK",
            bridge_mode="MOCK_ONLY",
            provider="mt5_mock",
            connected=False,
            terminal_detected=False,
            account_connected=False,
            login_required=False,
            real_mt5_imported=False,
            execution_allowed=False,
            safe_to_trade=False,
            real_trading=False,
            reason="mt5_bridge_mock_only",
            notes=["contract test"],
            **{loaded_secret_key(): False, send_available_key(): False},
        )

        payload = result.to_dict()

        self.assertEqual(payload["component"], "mt5_bridge")
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["bridge_mode"], "MOCK_ONLY")
        self.assertEqual(payload["provider"], "mt5_mock")
        self.assertIs(payload["connected"], False)
        self.assertIs(payload["terminal_detected"], False)
        self.assertIs(payload["account_connected"], False)
        self.assertIs(payload["login_required"], False)
        self.assertIs(payload[loaded_secret_key()], False)
        self.assertIs(payload["real_mt5_imported"], False)
        self.assertIs(payload[send_available_key()], False)
        self.assertIs(payload["execution_allowed"], False)
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)
        self.assertEqual(payload["reason"], "mt5_bridge_mock_only")


if __name__ == "__main__":
    unittest.main()
