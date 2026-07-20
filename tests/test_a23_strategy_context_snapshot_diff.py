import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from odin.cli import main
from odin.core.smoke import run_runtime_smoke
from odin.dashboard.routes import DashboardRoutes
from odin.decision.strategy_context_snapshot import (
    strategy_context_fingerprint,
    strategy_context_snapshot_status,
)
from odin.decision.strategy_context_snapshot_diff import strategy_context_snapshot_diff_status


class A23StrategyContextSnapshotDiffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _snapshot(self):
        return strategy_context_snapshot_status(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def _changed_snapshot(self):
        snapshot = self._snapshot()
        changed = dict(snapshot)
        changed["selected_source"] = "mt5_feed_mock_changed"
        quality = {
            "selected_source": changed["selected_source"],
            "primary_symbol": changed["primary_symbol"],
            "feed_quality_status": changed["feed_quality_status"],
            "data_quality_status": changed["data_quality_status"],
            "frame_quality_status": changed["frame_quality_status"],
            "strategy_status": changed["strategy_status"],
            "decision_intent_status": changed["decision_intent_status"],
            "risk_status": changed["risk_status"],
            "shadow_proposal_status": changed["shadow_proposal_status"],
            "gates_count": changed["quality_gates_count"],
            "all_gates_passed": changed["quality_gates_passed"],
        }
        changed["context_fingerprint"] = strategy_context_fingerprint(quality)
        return changed

    def test_valid_diff_is_deterministic_and_observational(self):
        before = self._snapshot()
        after = self._changed_snapshot()
        first = strategy_context_snapshot_diff_status(
            before_snapshot=before,
            after_snapshot=after,
        )
        second = strategy_context_snapshot_diff_status(
            before_snapshot=before,
            after_snapshot=after,
        )
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "OK")
        self.assertEqual(
            first["changed_fields"],
            ["selected_source", "context_fingerprint"],
        )
        self.assertFalse(first["execution_allowed"])
        self.assertFalse(first["safe_to_trade"])
        self.assertFalse(first["real_trading"])

    def test_missing_or_unsafe_snapshot_fails_closed(self):
        before = self._snapshot()
        blocked = strategy_context_snapshot_diff_status(
            before_snapshot=before,
            after_snapshot={},
        )
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertIn("after_snapshot_quality_blocked", blocked["blockers"])
        self.assertFalse(blocked["execution_allowed"])

        unsafe = self._snapshot()
        unsafe["execution_allowed"] = True
        blocked = strategy_context_snapshot_diff_status(
            before_snapshot=before,
            after_snapshot=unsafe,
        )
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertIn("critical_flags_not_blocked", blocked["blockers"])

    def test_cli_dashboard_and_smoke_expose_safe_diff(self):
        before = self._snapshot()
        after = self._changed_snapshot()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(
                [
                    "strategy-context-snapshot-diff",
                    "--before-json",
                    json.dumps(before),
                    "--after-json",
                    json.dumps(after),
                ]
            )
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "OK")

        route = DashboardRoutes(
            log_path=str(self.root / "logs" / "dashboard.jsonl"),
            sqlite_path=str(self.root / "runtime" / "dashboard.sqlite"),
        )
        status, payload = route.serve("/strategy/context/snapshot/diff")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "OK")

        smoke = run_runtime_smoke(
            log_path=str(self.root / "logs" / "smoke.jsonl"),
            sqlite_path=str(self.root / "runtime" / "smoke.sqlite"),
        )
        names = {str(module["name"]) for module in smoke["modules"]}
        self.assertIn("strategy-context-snapshot-diff", names)
        self.assertEqual(smoke["modules_count"], 21)
        self.assertEqual(smoke["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
