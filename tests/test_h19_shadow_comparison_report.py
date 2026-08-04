import json
import tempfile
import unittest
from pathlib import Path

from odin.reporting.shadow_comparison_report import write_shadow_comparison_report


class ShadowComparisonReportTests(unittest.TestCase):
    def test_persists_factual_comparison_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shadow = root / "shadow.json"
            shadow.write_text(json.dumps({
                "status": "OBSERVED_NO_DECISION", "reason": "fresh_demo_and_public_observations",
                "cycle_key": "same", "observed_at": "2026-08-04T15:00:00+00:00",
                "evidence": {"mt5_status": "CONNECTED_DEMO_READ_ONLY", "public_status": "OK", "public_fresh": True},
            }), encoding="utf-8")
            mt5 = root / "mt5.jsonl"
            mt5.write_text('{"event":"mt5_demo_readonly_snapshot"}\n', encoding="utf-8")
            public = root / "public.jsonl"
            public.write_text('{"event":"public_data.refresh.completed"}\n{"event":"public_data.refresh.failed"}\n', encoding="utf-8")
            first = write_shadow_comparison_report(output_dir=str(root / "reports"), shadow_state_path=str(shadow), mt5_audit_path=str(mt5), public_audit_path=str(public))
            second = write_shadow_comparison_report(output_dir=str(root / "reports"), shadow_state_path=str(shadow), mt5_audit_path=str(mt5), public_audit_path=str(public))
        self.assertEqual(first["status"], "OK")
        self.assertEqual(first["collection_history"]["public_failures"], 1)
        self.assertFalse(first["execution_allowed"])
        self.assertTrue(second["comparison"]["previous_report_available"])
        self.assertTrue(second["comparison"]["same_observation_inputs"])

    def test_missing_shadow_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = write_shadow_comparison_report(output_dir=str(Path(tmp) / "reports"), shadow_state_path=str(Path(tmp) / "none.json"))
        self.assertEqual(report["status"], "BLOCKED")
        self.assertFalse(report["execution_allowed"])
