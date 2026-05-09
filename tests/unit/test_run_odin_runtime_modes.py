from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_run_odin_runtime_modes() -> None:
    env = os.environ.copy()
    env["ODIN_SOAK_TEST_MINI_DURATION_SECONDS"] = "2"
    env["ODIN_SOAK_TEST_CYCLE_SLEEP_SECONDS"] = "0.1"

    for arg in ["--runtime-smoke-test", "--run-once", "--snapshot", "--runtime-validate", "--soak-test-mini"]:
        result = subprocess.run(
            ["./run_odin.sh", arg],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr + result.stdout
