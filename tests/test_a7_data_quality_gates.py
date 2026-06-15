import unittest

from odin.contracts.market_data import MarketSnapshot
from odin.data.gates import evaluate_snapshot


def snapshot(**overrides):
    data = {
        "symbol": "EURUSD",
        "bid": 1.08500,
        "ask": 1.08508,
        "spread": 0.00008,
        "timestamp": "2026-06-15T09:00:00+00:00",
        "source": "mock",
        "quality_status": "OK",
    }
    data.update(overrides)
    return MarketSnapshot(**data)


class A7DataQualityGatesTests(unittest.TestCase):
    def test_data_quality_report_returns_ok_for_mock_snapshot(self):
        report = evaluate_snapshot(snapshot()).to_dict()

        self.assertEqual(report["status"], "OK")
        self.assertEqual(report["component"], "data_quality")
        self.assertEqual(report["blocking_reasons"], [])

    def test_data_quality_has_all_required_gates(self):
        report = evaluate_snapshot(snapshot()).to_dict()
        gates = {gate["gate_name"] for gate in report["gates"]}

        expected = {
            "bid_present",
            "ask_present",
            "bid_positive",
            "ask_positive",
            "ask_greater_than_bid",
            "spread_present",
            "spread_non_negative",
            "spread_within_mock_limit",
            "timestamp_present",
            "source_present",
            "source_is_mock_for_a7",
        }
        self.assertEqual(gates, expected)
        self.assertEqual(report["gates_count"], 11)

    def test_bid_missing_blocks(self):
        self.assertEqual(evaluate_snapshot(snapshot(bid=None)).status, "INVALID")

    def test_ask_missing_blocks(self):
        self.assertEqual(evaluate_snapshot(snapshot(ask=None)).status, "INVALID")

    def test_bid_negative_blocks(self):
        self.assertEqual(evaluate_snapshot(snapshot(bid=-1.0)).status, "INVALID")

    def test_ask_negative_blocks(self):
        self.assertEqual(evaluate_snapshot(snapshot(ask=-1.0)).status, "INVALID")

    def test_ask_not_greater_than_bid_blocks(self):
        self.assertEqual(evaluate_snapshot(snapshot(bid=1.1, ask=1.0)).status, "INVALID")

    def test_spread_missing_blocks(self):
        self.assertEqual(evaluate_snapshot(snapshot(spread=None)).status, "INVALID")

    def test_spread_negative_blocks(self):
        self.assertEqual(evaluate_snapshot(snapshot(spread=-0.1)).status, "INVALID")

    def test_spread_too_high_blocks_or_warns(self):
        report = evaluate_snapshot(snapshot(spread=0.1))

        self.assertIn(report.status, {"INVALID", "WARNING"})

    def test_timestamp_missing_blocks(self):
        self.assertEqual(evaluate_snapshot(snapshot(timestamp="")).status, "INVALID")

    def test_source_missing_blocks(self):
        self.assertEqual(evaluate_snapshot(snapshot(source="")).status, "INVALID")

    def test_source_not_mock_blocks_for_a7(self):
        self.assertEqual(evaluate_snapshot(snapshot(source="external")).status, "INVALID")

    def test_safe_to_use_for_decision_false_even_when_ok(self):
        report = evaluate_snapshot(snapshot()).to_dict()

        self.assertIs(report["safe_to_use_for_decision"], False)

    def test_execution_allowed_false(self):
        self.assertIs(evaluate_snapshot(snapshot()).execution_allowed, False)

    def test_safe_to_trade_false(self):
        self.assertIs(evaluate_snapshot(snapshot()).safe_to_trade, False)

    def test_real_trading_false(self):
        self.assertIs(evaluate_snapshot(snapshot()).real_trading, False)


if __name__ == "__main__":
    unittest.main()

