from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_run_odin_runtime_modes() -> None:
    for arg in ["--runtime-smoke-test", "--run-once", "--snapshot"]:
        result = subprocess.run(
            ["./run_odin.sh", arg],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr + result.stdout
