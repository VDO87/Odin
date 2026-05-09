from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_runtime_commands_exposed_in_telegram_dry_run() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.telegram_bot.bot", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    out = result.stdout
    assert "/runtime" in out
    assert "/runtime_status" in out
    assert "/runtime_snapshot" in out
    assert "/runtime_events" in out
