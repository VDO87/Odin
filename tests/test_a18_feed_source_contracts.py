import unittest

from odin.contracts.feed_source import FeedSourceSelection


class A18FeedSourceContractTests(unittest.TestCase):
    def test_feed_source_contract_serializes(self):
        selection = FeedSourceSelection(
            component="feed_source_selector",
            status="OK",
            selector_mode="MOCK_ONLY",
            selected_source="mt5_feed_mock",
            fallback_source="market_data_mock",
            mt5_feed_quality_status="OK",
            mt5_feed_available=True,
            market_data_available=True,
            safe_to_use_for_decision=False,
            execution_allowed=False,
            safe_to_trade=False,
            real_trading=False,
            reason="feed_source_selector_mock_only",
            blockers=["decision_use_blocked"],
            notes=["contract test"],
        )

        payload = selection.to_dict()

        self.assertEqual(payload["component"], "feed_source_selector")
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["selector_mode"], "MOCK_ONLY")
        self.assertEqual(payload["selected_source"], "mt5_feed_mock")
        self.assertEqual(payload["fallback_source"], "market_data_mock")
        self.assertEqual(payload["mt5_feed_quality_status"], "OK")
        self.assertIs(payload["mt5_feed_available"], True)
        self.assertIs(payload["market_data_available"], True)
        self.assertIs(payload["safe_to_use_for_decision"], False)
        self.assertIs(payload["execution_allowed"], False)
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)
        self.assertEqual(payload["reason"], "feed_source_selector_mock_only")


if __name__ == "__main__":
    unittest.main()
