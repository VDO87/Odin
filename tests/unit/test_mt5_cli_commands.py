from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "apps.dashboard_terminal.cli", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_mt5_cli_status_commands_work_without_mt5() -> None:
    for args in [
        ("mt5-status",),
        ("mt5-healthcheck",),
        ("mt5-sync",),
        ("mt5-positions",),
        ("mt5-symbols",),
        ("mt5-tick", "EURUSD"),
        ("mt5-candles", "EURUSD", "M15", "50"),
    ]:
        result = _run(*args)
        assert result.returncode == 0, result.stderr + result.stdout
