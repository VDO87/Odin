from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, "-m", "apps.dashboard_terminal.cli", *args],
        cwd=ROOT,
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_runtime_validate_and_soak_commands(tmp_path: Path) -> None:
    env = {
        "ODIN_SOAK_TEST_OUTPUT_DIR": str(tmp_path / "soak"),
        "ODIN_SOAK_TEST_MINI_DURATION_SECONDS": "2",
        "ODIN_SOAK_TEST_CYCLE_SLEEP_SECONDS": "0.1",
    }
    for args in [
        ("runtime-validate",),
        ("soak-test", "--mini"),
        ("soak-report",),
    ]:
        result = _run(*args, env=env)
        assert result.returncode == 0, result.stderr + result.stdout
