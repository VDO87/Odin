import tempfile
import unittest
from pathlib import Path

from odin.core.smoke import run_runtime_smoke
from odin.decision.strategy_context_snapshot import strategy_context_snapshot_status


class A21StrategyContextSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _status(self, quality_report=None):
        return strategy_context_snapshot_status(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
            quality_report=quality_report,
        )

    def test_default_snapshot_is_observation_only(self):
        status = self._status()
        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["component"], "strategy_context_snapshot")
        self.assertEqual(status["snapshot_mode"], "MOCK_OBSERVATION_ONLY")
        self.assertEqual(status["snapshot_version"], "A21.v1")

    def test_snapshot_contains_approved_observational_context(self):
        status = self._status()
        self.assertEqual(status["selected_source"], "mt5_feed_mock")
        self.assertEqual(status["primary_symbol"], "EURUSD")
        self.assertEqual(status["frame_quality_status"], "OK")
        self.assertEqual(status["strategy_status"], "READY_NO_DECISION")
        self.assertEqual(status["risk_status"], "BLOCKED")
        self.assertGreaterEqual(status["quality_gates_count"], 12)
        self.assertIs(status["quality_gates_passed"], True)

    def test_fingerprint_is_deterministic_across_runs(self):
        first = self._status()
        second = self._status()
        self.assertEqual(first["context_fingerprint"], second["context_fingerprint"])
        self.assertEqual(len(first["context_fingerprint"]), 64)

    def test_fingerprint_changes_when_observational_context_changes(self):
        valid = self._status()
        changed = dict(valid)
        changed.update(
            {
                "status": "OK",
                "all_gates_passed": True,
                "gates_count": valid["quality_gates_count"],
                "primary_symbol": "GBPUSD",
            }
        )
        result = self._status(changed)
        self.assertNotEqual(result["context_fingerprint"], valid["context_fingerprint"])

    def test_invalid_a20_input_fails_closed(self):
        result = self._status(
            {
                "status": "INVALID",
                "frame_quality_status": "INVALID",
                "all_gates_passed": False,
            }
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "a20_quality_invalid")
        self.assertIn("a20_quality_not_approved", result["blockers"])

    def test_all_critical_flags_remain_false(self):
        status = self._status()
        for key in (
            "safe_to_use_for_decision",
            "decision_generated",
            "trade_proposal_generated",
            "risk_approved",
            "execution_allowed",
            "safe_to_trade",
            "real_trading",
        ):
            self.assertIs(status[key], False)

    def test_smoke_includes_strategy_context_snapshot(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )
        names = {str(module["name"]) for module in report["modules"]}
        self.assertIn("strategy-context-snapshot", names)
        self.assertEqual(report["modules_count"], 21)
        self.assertEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
