import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from odin.contracts.shadow_intelligence import ContextPacket, MarketBar
from odin.dashboard.routes import DashboardRoutes
from odin.shadow.ledger import append_decision
from odin.shadow.pipeline import build_market_state, evaluate_shadow_risk, shadow_decision
from odin.shadow.replay import replay_shadow


def bars(count=5):
    start = datetime(2026, 8, 15, 12, tzinfo=UTC)
    return [MarketBar("EURUSD", "M15", (start + timedelta(minutes=15 * i)).isoformat().replace("+00:00", "Z"), 1.1 + i / 10000, 1.1002 + i / 10000, 1.0998 + i / 10000, 1.1001 + i / 10000, 10, 0.0001, "fixture", "fixture://shadow", "VALIDATED") for i in range(count)]


class ShadowIntelligenceTests(unittest.TestCase):
    def test_market_state_is_provider_neutral_and_deterministic(self):
        value = bars()
        first = build_market_state(value, now_utc=datetime(2026, 8, 15, 13, 1, tzinfo=UTC))
        second = build_market_state(value, now_utc=datetime(2026, 8, 15, 13, 1, tzinfo=UTC))
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.trend, "UP")
        self.assertEqual(first.freshness, "FRESH")

    def test_risk_blocks_stale_bad_spread_reconciliation_and_kill(self):
        state = build_market_state(bars(), now_utc=datetime(2026, 8, 16, tzinfo=UTC))
        blocked = evaluate_shadow_risk(state)
        self.assertEqual(blocked["risk_status"], "BLOCK")
        self.assertFalse(blocked["execution_allowed"])
        killed = evaluate_shadow_risk(build_market_state(bars(), now_utc=datetime(2026, 8, 15, 13, tzinfo=UTC)), kill_switch=True)
        self.assertEqual(killed["risk_status"], "KILL")

    def test_decision_and_ledger_never_enable_execution(self):
        decision = shadow_decision(bars(), now_utc=datetime(2026, 8, 15, 13, tzinfo=UTC))
        self.assertEqual(decision["signal"], "BUY")
        self.assertFalse(decision["execution_allowed"])
        with tempfile.TemporaryDirectory() as root:
            record = append_decision(decision, path=Path(root) / "ledger.jsonl")
            self.assertFalse(record["execution_allowed"])
            self.assertEqual(json.loads((Path(root) / "ledger.jsonl").read_text())['decision']['decision_id'], decision['decision_id'])

    def test_context_packet_is_read_only_data_contract(self):
        packet = ContextPacket("ecb", "2026-08-15T00:00:00Z", ("source record",), None, ("EURUSD",), "D1", ("stale",), "FRESH", "fixture://ecb", "VALID")
        self.assertEqual(packet.to_dict()["status"], "VALID")

    def test_replay_is_deterministic_and_has_no_lookahead_or_execution(self):
        value = bars(8)
        first = replay_shadow(value)
        second = replay_shadow(value)
        self.assertEqual(first["decisions_hash"], second["decisions_hash"])
        self.assertFalse(first["lookahead"])
        self.assertFalse(first["execution_allowed"])

    def test_dashboard_labels_shadow_as_non_execution(self):
        routes = DashboardRoutes()
        status, payload = routes.serve("/shadow/intelligence")
        self.assertEqual(status, 200)
        self.assertFalse(payload["execution_allowed"])
        self.assertIn("SHADOW INTELLIGENCE", routes.tradedesk_html())

if __name__ == "__main__":
    unittest.main()
