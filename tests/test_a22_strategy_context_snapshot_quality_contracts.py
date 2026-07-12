import dataclasses
import unittest

from odin.contracts.strategy_context_snapshot_quality import StrategyContextSnapshotQualityReport


class A22StrategyContextSnapshotQualityContractTests(unittest.TestCase):
    def _report(self):
        return StrategyContextSnapshotQualityReport(
            component="strategy_context_snapshot_quality",
            status="OK",
            quality_mode="SNAPSHOT_QUALITY_GATE",
            quality_version="A22.v1",
            snapshot_mode="MOCK_OBSERVATION_ONLY",
            snapshot_version="A21.v1",
            selected_source="mt5_feed_mock",
            primary_symbol="EURUSD",
            context_fingerprint="a" * 64,
            recomputed_fingerprint="a" * 64,
            fingerprint_valid=True,
            schema_valid=True,
            required_fields_present=True,
            quality_gates_passed=True,
            flags_blocked=True,
            gates_count=9,
            gates_passed=9,
            safe_to_use_for_decision=False,
            decision_generated=False,
            proposal_generated=False,
            risk_approved=False,
            execution_allowed=False,
            safe_to_trade=False,
            real_trading=False,
            reason="strategy_context_snapshot_quality_passed",
            gates=("fingerprint_valid",),
            blockers=(),
            notes=("contract test",),
        )

    def test_contract_is_frozen(self):
        report = self._report()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            report.status = "CHANGED"  # type: ignore[misc]

    def test_contract_serializes_lists_and_critical_flags(self):
        payload = self._report().to_dict()
        self.assertEqual(payload["gates"], ["fingerprint_valid"])
        self.assertEqual(payload["notes"], ["contract test"])
        self.assertIs(payload["trade_proposal_generated"], False)
        self.assertIs(payload["safe_to_use_for_decision"], False)
        self.assertIs(payload["execution_allowed"], False)


if __name__ == "__main__":
    unittest.main()
