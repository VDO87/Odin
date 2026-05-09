from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_update_runtime_dry_run() -> None:
    result = subprocess.run(
        ["./scripts/update_odin_runtime.sh", "--dry-run", "--backup-first"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
