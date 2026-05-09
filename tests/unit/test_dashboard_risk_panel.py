from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_risk_panel_has_operational_fields() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_html.app", "--export-preview"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    body = (ROOT / "dashboard_preview" / "index.html").read_text(encoding="utf-8")
    assert "Risk Engine" in body
    assert "Risk per trade" in body
    assert "Max daily loss" in body
    assert "Consecutive losses" in body
