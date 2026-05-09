from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_soak_test_runner_mini_offline(tmp_path: Path) -> None:
    out_dir = tmp_path / "soak"
    report = tmp_path / "soak_result.md"
    json_output = tmp_path / "soak_result.json"

    env = os.environ.copy()
    env["ODIN_SOAK_TEST_OUTPUT_DIR"] = str(out_dir)
    env["ODIN_SOAK_TEST_MINI_DURATION_SECONDS"] = "2"
    env["ODIN_SOAK_TEST_CYCLE_SLEEP_SECONDS"] = "0.1"
    env["ENABLE_REAL_TRADING"] = "false"
    env["MT5_ORDER_SEND_ENABLED"] = "false"
    env["XTB_REAL_ENABLED"] = "false"
    env["BROKER_ALLOW_REAL_EXECUTION"] = "false"
    env["OPENAI_SUPPORT_ENABLED"] = "false"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.odin_soak_test",
            "--mini",
            "--offline-ok",
            "--no-network-required",
            "--report",
            str(report),
            "--json-output",
            str(json_output),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    latest = out_dir / "latest_soak_result.json"
    assert latest.exists()
    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert payload["summary"]["no_order_attempts"] is True
    assert payload["summary"]["dangerous_commands_blocked"] is True
