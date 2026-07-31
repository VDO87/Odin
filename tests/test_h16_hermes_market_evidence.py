import unittest

from odin.hermes.summary import build_hermes_summary


class HermesMarketEvidenceTests(unittest.TestCase):
    def test_summary_exposes_only_safe_public_cache_metadata(self):
        state = {"safe_to_trade": False, "real_trading": False, "hermes_mode": "READ_ONLY", "risk_state": "READY_BLOCKING"}
        evidence = {"status": "OK", "latest_source": "ecb_exr", "fresh": True, "records_count": 2, "latest_content_hash": "abc", "hidden_body": "remote text"}
        result = build_hermes_summary(state=state, log_events=[], market_evidence=evidence)
        view = result["market_evidence"]
        self.assertEqual(view["source"], "ecb_exr")
        self.assertTrue(view["fresh"])
        self.assertNotIn("hidden_body", view)
        self.assertFalse(view["safe_to_use_for_decision"])
        self.assertFalse(view["execution_allowed"])


if __name__ == "__main__":
    unittest.main()
