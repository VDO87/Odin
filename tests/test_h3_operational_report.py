import json
import tempfile
import unittest
from pathlib import Path

from odin.reporting.operational_report import write_operational_report


class OperationalReportTests(unittest.TestCase):
    def test_report_is_written_with_safe_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = write_operational_report(
                output_dir=str(root / "reports"),
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            written = json.loads(Path(str(report["report_path"])).read_text(encoding="utf-8"))

        self.assertEqual(report["status"], "OK")
        self.assertIs(report["execution_allowed"], False)
        self.assertIs(report["safe_to_trade"], False)
        self.assertIs(report["real_trading"], False)
        self.assertEqual(written["component"], "operational_report")
        self.assertIs(written["overview"]["read_only"], True)


if __name__ == "__main__":
    unittest.main()
