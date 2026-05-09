from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_sparkline_is_always_visible() -> None:
    env = os.environ.copy()
    env["ODIN_DASHBOARD_FORCE_DEMO"] = "true"
    result = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_html.app", "--export-preview"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    body = (ROOT / "dashboard_preview" / "index.html").read_text(encoding="utf-8")
    assert "SPARKLINE" in body
    assert "n/a" not in body.lower().split("sparkline", 1)[-1][:40]
    assert "DEMO DATA" in body
