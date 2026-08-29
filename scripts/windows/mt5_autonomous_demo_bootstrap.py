"""Local Windows bootstrap for the versioned Autonomous DEMO RC2 runtime."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
RESTART_DELAYS_SECONDS = (5, 30, 60)
WATCHDOG_LOG = Path(r"D:\ODIN_LOCAL\logs\autonomous-demo\watchdog.jsonl")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--canonical-repo-root", required=True)
    parser.add_argument("--persistent-task", action="store_true")
    arguments = parser.parse_args()

    runtime_root = Path(arguments.runtime_root).resolve()
    installed_root = Path(__file__).resolve().parents[2]
    if runtime_root != installed_root:
        raise RuntimeError("rc2_installed_runtime_root_mismatch")

    source_root = runtime_root / "src"
    windows_scripts = runtime_root / "scripts" / "windows"
    supervisor = windows_scripts / "mt5_autonomous_demo_supervisor.py"
    if not source_root.is_dir() or not supervisor.is_file():
        raise RuntimeError("rc2_installed_runtime_incomplete")

    os.environ["ODIN_RC2_CANONICAL_REPO_ROOT"] = arguments.canonical_repo_root
    os.environ["ODIN_RC2_REPO_SRC"] = str(source_root)
    os.environ["ODIN_RC2_WINDOWS_SCRIPTS"] = str(windows_scripts)
    os.environ["ODIN_RC1_REPO_SRC"] = str(source_root)
    command = [sys.executable, str(supervisor)]
    if arguments.persistent_task:
        command.append("--persistent-task")
    return _supervise(command)


def _supervise(
    command: list[str],
    *,
    popen: Callable[..., Any] = subprocess.Popen,
    sleep: Callable[[float], None] = time.sleep,
    record: Callable[[dict[str, object]], None] | None = None,
) -> int:
    write_event = record or _append_watchdog_event
    for restart_attempt in range(len(RESTART_DELAYS_SECONDS) + 1):
        child = popen(command, creationflags=CREATE_NO_WINDOW)
        return_code = int(child.wait())
        if return_code == 0:
            write_event(
                _watchdog_event(
                    "SUPERVISOR_EXITED_CLEANLY",
                    child_pid=int(child.pid),
                    return_code=return_code,
                    restart_attempt=restart_attempt,
                    restart_delay_seconds=0,
                )
            )
            return 0
        if restart_attempt >= len(RESTART_DELAYS_SECONDS):
            write_event(
                _watchdog_event(
                    "SUPERVISOR_RESTART_BUDGET_EXHAUSTED",
                    child_pid=int(child.pid),
                    return_code=return_code,
                    restart_attempt=restart_attempt,
                    restart_delay_seconds=0,
                )
            )
            return return_code or 1
        delay = RESTART_DELAYS_SECONDS[restart_attempt]
        write_event(
            _watchdog_event(
                "SUPERVISOR_RESTART_SCHEDULED",
                child_pid=int(child.pid),
                return_code=return_code,
                restart_attempt=restart_attempt + 1,
                restart_delay_seconds=delay,
            )
        )
        sleep(delay)
    raise AssertionError("unreachable")


def _watchdog_event(
    event: str,
    *,
    child_pid: int,
    return_code: int,
    restart_attempt: int,
    restart_delay_seconds: int,
) -> dict[str, object]:
    return {
        "schema": "odin.autonomous_demo_watchdog/v1",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "event": event,
        "child_pid": child_pid,
        "return_code": return_code,
        "restart_attempt": restart_attempt,
        "restart_delay_seconds": restart_delay_seconds,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
        "broker_submission_called": False,
    }


def _append_watchdog_event(event: dict[str, object]) -> None:
    WATCHDOG_LOG.parent.mkdir(parents=True, exist_ok=True)
    with WATCHDOG_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
