import unittest

from odin.data.dukascopy_history import DukascopyHistoryError, aggregate_m1_to_m15, decode_minute_payload


class DukascopyHistoryTests(unittest.TestCase):
    def test_decodes_vendor_delta_payload_and_aggregates_complete_utc_window(self):
        payload = {
            "timestamp": 0, "shift": 60000, "multiplier": 0.00001,
            "open": 1.10000, "high": 1.10000, "low": 1.10000, "close": 1.10000,
            "times": [0] + [1] * 14, "opens": [0] * 15, "highs": [2] * 15,
            "lows": [-2] * 15, "closes": [2] * 15, "volumes": [1] * 15,
        }
        m15 = aggregate_m1_to_m15(decode_minute_payload(payload))
        self.assertEqual(len(m15), 1)
        self.assertEqual(m15[0]["timestamp_ms"], 0)
        self.assertEqual(m15[0]["open"], 1.1)
        self.assertEqual(m15[0]["close"], 1.1003)
        self.assertEqual(m15[0]["volume"], 15.0)

    def test_rejects_incomplete_or_non_monotonic_m1_windows(self):
        incomplete = [{"timestamp_ms": index * 60000, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0} for index in range(14)]
        with self.assertRaisesRegex(DukascopyHistoryError, "incomplete"):
            aggregate_m1_to_m15(incomplete)
        unordered = [
            {"timestamp_ms": 60000, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
            {"timestamp_ms": 0, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
        ]
        with self.assertRaisesRegex(DukascopyHistoryError, "ordering"):
            aggregate_m1_to_m15(unordered)

    def test_accepts_an_explicit_vendor_market_closure_payload(self):
        payload = {"timestamp": 0, "shift": 60000, "multiplier": 0.00001, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0,
                   "times": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
        self.assertEqual(decode_minute_payload(payload), [])
