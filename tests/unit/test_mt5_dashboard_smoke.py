from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_smoke_includes_mt5_route() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_html.app", "--smoke-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "smoke-test" in result.stdout.lower()
