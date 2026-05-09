from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_run_odin_dashboard_modes(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["ODIN_DASHBOARD_PREVIEW_DIR"] = str(tmp_path / "preview")
    commands = [
        ["./run_odin.sh", "--dashboard-preview"],
        ["./run_odin.sh", "--dashboard-qa"],
        ["./run_odin.sh", "--tui-smoke-test"],
        ["./run_odin.sh", "--tui-once"],
    ]
    for cmd in commands:
        result = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr + result.stdout
