from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_tui_smoke_and_once() -> None:
    smoke = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_tui.app", "--smoke-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert smoke.returncode == 0, smoke.stderr + smoke.stdout

    once = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_tui.app", "--once", "--demo"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert once.returncode == 0, once.stderr + once.stdout
    assert "COMMAND BAR" in once.stdout
