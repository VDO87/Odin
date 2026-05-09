from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_uninstall_runtime_dry_run() -> None:
    result = subprocess.run(
        ["./scripts/uninstall_odin_runtime.sh", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
