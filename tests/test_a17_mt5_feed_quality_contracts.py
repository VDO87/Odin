import unittest

from odin.contracts.mt5_feed_quality import MT5FeedQualityGate, MT5FeedQualityReport


class A17MT5FeedQualityContractTests(unittest.TestCase):
    def test_mt5_feed_quality_gate_serializes(self):
        gate = MT5FeedQualityGate(
            symbol="EURUSD",
            gate_name="bid_positive",
            passed=True,
            status="PASS",
            blocking=True,
            reason="gate_passed",
            details={"bid": 1.08500},
        )

        payload = gate.to_dict()

        self.assertEqual(payload["symbol"], "EURUSD")
        self.assertEqual(payload["gate_name"], "bid_positive")
        self.assertIs(payload["passed"], True)
        self.assertEqual(payload["status"], "PASS")
        self.assertIs(payload["blocking"], True)
        self.assertEqual(payload["reason"], "gate_passed")
        self.assertEqual(payload["details"], {"bid": 1.08500})

    def test_mt5_feed_quality_report_serializes(self):
        gate = MT5FeedQualityGate(
            symbol="EURUSD",
            gate_name="execution_blocked",
            passed=True,
            status="PASS",
            blocking=True,
            reason="gate_passed",
            details={"execution_allowed": False},
        )
        report = MT5FeedQualityReport(
            component="mt5_feed_quality",
            status="OK",
            quality_mode="MOCK_FEED_GATES",
            provider="mt5_mock",
            source="mt5_mock",
            symbols_checked=1,
            gates_count=1,
            all_ticks_valid=True,
            safe_to_use_for_decision=False,
            execution_allowed=False,
            safe_to_trade=False,
            real_trading=False,
            reason="mt5_feed_quality_mock_passed",
            gates=[gate],
            blockers=[],
            notes=["contract test"],
        )

        payload = report.to_dict()

        self.assertEqual(payload["component"], "mt5_feed_quality")
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["quality_mode"], "MOCK_FEED_GATES")
        self.assertEqual(payload["provider"], "mt5_mock")
        self.assertEqual(payload["source"], "mt5_mock")
        self.assertEqual(payload["symbols_checked"], 1)
        self.assertEqual(payload["gates_count"], 1)
        self.assertIs(payload["all_ticks_valid"], True)
        self.assertIs(payload["safe_to_use_for_decision"], False)
        self.assertIs(payload["execution_allowed"], False)
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)
        self.assertEqual(len(payload["gates"]), 1)


if __name__ == "__main__":
    unittest.main()
