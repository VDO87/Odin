from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_export_preview_creates_files(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["ODIN_DASHBOARD_PREVIEW_DIR"] = str(tmp_path / "dashboard_preview")
    result = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_html.app", "--export-preview"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    preview = tmp_path / "dashboard_preview"
    for name in ["index.html", "runtime.html", "mt5.html", "atlas.html", "assistant.html", "logs.html", "README_PREVIEW.md"]:
        assert (preview / name).exists(), name
