import dataclasses
import unittest

from odin.contracts.strategy_context_snapshot import StrategyContextSnapshot


class A21StrategyContextSnapshotContractTests(unittest.TestCase):
    def _snapshot(self):
        return StrategyContextSnapshot(
            component="strategy_context_snapshot",
            status="OK",
            snapshot_mode="MOCK_OBSERVATION_ONLY",
            snapshot_version="A21.v1",
            selected_source="mt5_feed_mock",
            primary_symbol="EURUSD",
            feed_quality_status="OK",
            data_quality_status="OK",
            frame_quality_status="OK",
            strategy_status="READY_NO_DECISION",
            decision_intent_status="NO_DECISION",
            risk_status="BLOCKED",
            shadow_proposal_status="BLOCKED",
            quality_gates_count=20,
            quality_gates_passed=True,
            context_fingerprint="a" * 64,
            safe_to_use_for_decision=False,
            decision_generated=False,
            proposal_generated=False,
            risk_approved=False,
            execution_allowed=False,
            safe_to_trade=False,
            real_trading=False,
            reason="strategy_context_snapshot_mock_ready",
            blockers=("decision_use_blocked",),
            notes=("contract test",),
        )

    def test_contract_is_frozen(self):
        snapshot = self._snapshot()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            snapshot.status = "CHANGED"  # type: ignore[misc]

    def test_contract_serializes_lists_and_critical_flags(self):
        payload = self._snapshot().to_dict()
        self.assertEqual(payload["context_fingerprint"], "a" * 64)
        self.assertEqual(payload["blockers"], ["decision_use_blocked"])
        self.assertEqual(payload["notes"], ["contract test"])
        self.assertIs(payload["trade_proposal_generated"], False)
        self.assertIs(payload["execution_allowed"], False)


if __name__ == "__main__":
    unittest.main()
