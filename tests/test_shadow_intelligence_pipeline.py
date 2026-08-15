import json
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from odin.contracts.shadow_intelligence import ContextPacket, MarketBar
from odin.dashboard.routes import DashboardRoutes
from odin.shadow.ledger import append_decision
from odin.shadow.market_data import from_mt5_observation, from_replay_candles
from odin.shadow.context import context_from_public_observation
from odin.shadow.service import run_shadow_cycle
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

    def test_risk_covers_bad_missing_spread_reconciliation_and_drawdown(self):
        fresh = build_market_state(bars(), now_utc=datetime(2026, 8, 15, 13, tzinfo=UTC))
        self.assertEqual(evaluate_shadow_risk(replace(fresh, data_quality="DEGRADED"))["risk_status"], "BLOCK")
        self.assertEqual(evaluate_shadow_risk(build_market_state([], now_utc=datetime(2026, 8, 15, tzinfo=UTC)))["risk_status"], "BLOCK")
        self.assertEqual(evaluate_shadow_risk(replace(fresh, spread_proxy=0.1))["risk_status"], "BLOCK")
        self.assertEqual(evaluate_shadow_risk(replace(fresh, source_reconciliation_status="UNRECONCILED"))["risk_status"], "BLOCK")
        self.assertEqual(evaluate_shadow_risk(fresh, simulated_drawdown_percent=10.0)["risk_status"], "RESTRICT")

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
        self.assertIn("SHADOW INTELLIGENCE", routes.cockpit_html())

    def test_all_inputs_normalize_to_marketbar_without_strategy_provider_branch(self):
        replay = from_replay_candles([{"timestamp": "2026-08-15T12:00:00Z", "open": 1.1, "high": 1.2, "low": 1.0, "close": 1.15, "volume": 5, "spread": 0.0001}], symbol="EURUSD", timeframe="M15")
        mt5 = from_mt5_observation({"status": "CONNECTED_DEMO_READ_ONLY", "fresh": True, "content_hash": "hash", "market": {"status": "OK", "symbol": "EURUSD", "spread": 0.0001, "candles": [{"time": "2026-08-15T12:00:00Z", "open": 1.1, "high": 1.2, "low": 1.0, "close": 1.15}]}})
        self.assertEqual(type(replay[0]), type(mt5[0]))
        self.assertEqual(shadow_decision(replay, now_utc=datetime(2026, 8, 15, 12, 1, tzinfo=UTC))["execution_allowed"], False)

    def test_context_is_evidence_only_and_never_changes_risk(self):
        packet = context_from_public_observation({"status": "OK", "fresh": True, "source": "ecb", "source_url": "https://example.test", "content_hash": "abc"})
        self.assertEqual(packet.status, "VALID")
        decision = shadow_decision(bars(), now_utc=datetime(2026, 8, 15, 13, tzinfo=UTC))
        self.assertEqual(decision["risk_result"]["risk_status"], "ALLOW_SHADOW")

    def test_sanitized_mt5_cycle_writes_shadow_ledger_without_execution(self):
        state = {"status": "CONNECTED_DEMO_READ_ONLY", "fresh": True, "content_hash": "hash", "market": {"status": "OK", "symbol": "EURUSD", "spread": 0.0001, "candles": [{"time": "2026-08-15T12:00:00Z", "open": 1.1, "high": 1.2, "low": 1.0, "close": 1.15}]}}
        with tempfile.TemporaryDirectory() as root:
            state_path = Path(root) / "mt5.json"
            state_path.write_text(json.dumps(state))
            result = run_shadow_cycle(mt5_state_path=state_path, ledger_path=Path(root) / "ledger.jsonl")
            self.assertFalse(result["execution_allowed"])
            self.assertTrue(result["ledger_record_hash"])

if __name__ == "__main__":
    unittest.main()
