from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_visual_qa_generates_report() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_html.app", "--dashboard-qa"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    report = ROOT / "docs/reports/ODIN_DASHBOARD_VISUAL_QA_REPORT.md"
    assert report.exists()
    content = report.read_text(encoding="utf-8")
    assert "Status" in content
    assert "TRADING REAL: BLOCKED" in content
