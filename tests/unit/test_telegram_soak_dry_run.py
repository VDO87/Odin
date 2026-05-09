from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_telegram_dry_run_includes_soak_commands() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.telegram_bot.bot", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    out = result.stdout
    assert "/soak" in out
    assert "/soak_status" in out
    assert "/soak_report" in out
    assert "/runtime_validate" in out
