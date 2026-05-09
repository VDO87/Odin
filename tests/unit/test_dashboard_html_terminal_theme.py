from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_html_contains_terminal_theme_and_badges(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["ODIN_DASHBOARD_PREVIEW_DIR"] = str(tmp_path / "preview")
    result = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_html.app", "--export-preview"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout

    index = (tmp_path / "preview" / "index.html").read_text(encoding="utf-8")
    assert "/static/odin_terminal.css" in index
    assert "TRADING REAL: BLOCKED" in index
    assert "MT5 ORDER_SEND: BLOCKED" in index
    assert "BROKER REAL: BLOCKED" in index
