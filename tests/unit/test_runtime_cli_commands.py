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


def test_runtime_cli_commands() -> None:
    for args in [
        ("runtime-status",),
        ("runtime-run-once",),
        ("runtime-snapshot",),
        ("runtime-events",),
        ("runtime-smoke-test",),
    ]:
        result = _run(*args)
        assert result.returncode == 0, result.stderr + result.stdout
