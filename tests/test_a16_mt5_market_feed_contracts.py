import unittest

from odin.contracts.mt5_market_feed import MT5FeedTick, MT5MarketFeedReport, tradable_key


class A16MT5MarketFeedContractTests(unittest.TestCase):
    def test_mt5_feed_tick_serializes(self):
        tick = MT5FeedTick(
            symbol="EURUSD",
            bid=1.08500,
            ask=1.08508,
            spread=0.00008,
            timestamp="2026-01-01T00:00:00+00:00",
            source="mt5_mock",
            tradable=True,
            execution_allowed=False,
        )

        payload = tick.to_dict()

        self.assertEqual(payload["symbol"], "EURUSD")
        self.assertEqual(payload["bid"], 1.08500)
        self.assertEqual(payload["ask"], 1.08508)
        self.assertEqual(payload["spread"], 0.00008)
        self.assertEqual(payload["source"], "mt5_mock")
        self.assertIs(payload[tradable_key()], True)
        self.assertIs(payload["execution_allowed"], False)

    def test_mt5_feed_report_serializes(self):
        tick = MT5FeedTick(
            symbol="EURUSD",
            bid=1.08500,
            ask=1.08508,
            spread=0.00008,
            timestamp="2026-01-01T00:00:00+00:00",
            source="mt5_mock",
            tradable=True,
            execution_allowed=False,
        )
        report = MT5MarketFeedReport(
            component="mt5_market_feed",
            status="OK",
            feed_mode="MOCK_ONLY",
            provider="mt5_mock",
            source="mt5_mock",
            connected=False,
            real_mt5_imported=False,
            symbols_count=1,
            primary_symbol="EURUSD",
            execution_allowed=False,
            safe_to_trade=False,
            real_trading=False,
            reason="mt5_market_feed_mock_only",
            ticks=[tick],
            notes=["contract test"],
        )

        payload = report.to_dict()

        self.assertEqual(payload["component"], "mt5_market_feed")
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["feed_mode"], "MOCK_ONLY")
        self.assertEqual(payload["provider"], "mt5_mock")
        self.assertEqual(payload["source"], "mt5_mock")
        self.assertIs(payload["connected"], False)
        self.assertIs(payload["real_mt5_imported"], False)
        self.assertEqual(payload["symbols_count"], 1)
        self.assertEqual(payload["primary_symbol"], "EURUSD")
        self.assertIs(payload["execution_allowed"], False)
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)
        self.assertEqual(len(payload["ticks"]), 1)


if __name__ == "__main__":
    unittest.main()
