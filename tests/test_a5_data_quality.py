import unittest

from odin.contracts.market_data import MarketSnapshot
from odin.data.quality import check_snapshot_quality


class A5DataQualityTests(unittest.TestCase):
    def test_data_quality_ok_for_valid_snapshot(self):
        snapshot = MarketSnapshot(
            symbol="EURUSD",
            bid=1.08500,
            ask=1.08508,
            spread=0.00008,
            timestamp="2026-06-15T09:00:00+00:00",
            source="mock",
            quality_status="OK",
        )

        quality = check_snapshot_quality(snapshot)

        self.assertEqual(quality.status, "OK")
        self.assertEqual(quality.missing_fields, [])
        self.assertIs(quality.spread_ok, True)
        self.assertIs(quality.timestamp_ok, True)
        self.assertIs(quality.source_ok, True)

    def test_data_quality_invalid_when_missing_bid(self):
        snapshot = MarketSnapshot(
            symbol="EURUSD",
            bid=None,
            ask=1.08508,
            spread=0.00008,
            timestamp="2026-06-15T09:00:00+00:00",
            source="mock",
            quality_status="INVALID",
        )

        quality = check_snapshot_quality(snapshot)

        self.assertEqual(quality.status, "INVALID")
        self.assertIn("bid", quality.missing_fields)


if __name__ == "__main__":
    unittest.main()

