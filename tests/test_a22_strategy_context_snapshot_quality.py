import tempfile
import unittest
from pathlib import Path

from odin.core.smoke import run_runtime_smoke
from odin.decision.strategy_context_snapshot import strategy_context_snapshot_status
from odin.decision.strategy_context_snapshot_quality import strategy_context_snapshot_quality_status


class A22StrategyContextSnapshotQualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _quality(self, snapshot=None):
        return strategy_context_snapshot_quality_status(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
            snapshot=snapshot,
        )

    def _snapshot(self):
        return strategy_context_snapshot_status(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def test_valid_snapshot_passes_quality_gate(self):
        result = self._quality()
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["component"], "strategy_context_snapshot_quality")
        self.assertEqual(result["quality_mode"], "SNAPSHOT_QUALITY_GATE")
        self.assertEqual(result["quality_version"], "A22.v1")
        self.assertIs(result["fingerprint_valid"], True)
        self.assertEqual(result["gates_count"], 9)
        self.assertEqual(result["gates_passed"], 9)

    def test_fingerprint_altered_fails_closed(self):
        snapshot = self._snapshot()
        snapshot["context_fingerprint"] = "0" * 64
        result = self._quality(snapshot)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("fingerprint_valid", result["blockers"])
        self.assertIs(result["safe_to_trade"], False)

    def test_wrong_version_fails_closed(self):
        snapshot = self._snapshot()
        snapshot["snapshot_version"] = "A99.v1"
        result = self._quality(snapshot)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("snapshot_version_valid", result["blockers"])

    def test_wrong_mode_fails_closed(self):
        snapshot = self._snapshot()
        snapshot["snapshot_mode"] = "LIVE"
        result = self._quality(snapshot)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("snapshot_mode_valid", result["blockers"])

    def test_missing_required_field_fails_closed(self):
        snapshot = self._snapshot()
        del snapshot["primary_symbol"]
        result = self._quality(snapshot)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("required_fields_present", result["blockers"])

    def test_empty_source_or_symbol_fails_closed(self):
        snapshot = self._snapshot()
        snapshot["selected_source"] = ""
        result = self._quality(snapshot)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("source_present", result["blockers"])

        snapshot = self._snapshot()
        snapshot["primary_symbol"] = " "
        result = self._quality(snapshot)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("symbol_present", result["blockers"])

    def test_any_critical_flag_true_fails_closed(self):
        for key in (
            "safe_to_use_for_decision",
            "decision_generated",
            "trade_proposal_generated",
            "risk_approved",
            "execution_allowed",
            "safe_to_trade",
            "real_trading",
        ):
            snapshot = self._snapshot()
            snapshot[key] = True
            result = self._quality(snapshot)
            self.assertEqual(result["status"], "BLOCKED", key)
            self.assertIn("flags_blocked", result["blockers"])
            self.assertIs(result["execution_allowed"], False)

    def test_invalid_input_never_unlocks_runtime(self):
        result = self._quality({"snapshot_mode": "LIVE"})
        self.assertEqual(result["status"], "BLOCKED")
        for key in (
            "safe_to_use_for_decision",
            "decision_generated",
            "trade_proposal_generated",
            "risk_approved",
            "execution_allowed",
            "safe_to_trade",
            "real_trading",
        ):
            self.assertIs(result[key], False)

    def test_smoke_includes_strategy_context_snapshot_quality(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )
        names = {str(module["name"]) for module in report["modules"]}
        self.assertIn("strategy-context-snapshot-quality", names)
        self.assertEqual(report["modules_count"], 19)
        self.assertEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
