"""Local Windows bootstrap for the versioned Autonomous DEMO RC2 runtime."""

from __future__ import annotations

import argparse
from collections.abc import Callable
import ctypes
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
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("read_operation_count", ctypes.c_ulonglong),
        ("write_operation_count", ctypes.c_ulonglong),
        ("other_operation_count", ctypes.c_ulonglong),
        ("read_transfer_count", ctypes.c_ulonglong),
        ("write_transfer_count", ctypes.c_ulonglong),
        ("other_transfer_count", ctypes.c_ulonglong),
    ]


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("per_process_user_time_limit", ctypes.c_longlong),
        ("per_job_user_time_limit", ctypes.c_longlong),
        ("limit_flags", ctypes.c_ulong),
        ("minimum_working_set_size", ctypes.c_size_t),
        ("maximum_working_set_size", ctypes.c_size_t),
        ("active_process_limit", ctypes.c_ulong),
        ("affinity", ctypes.c_size_t),
        ("priority_class", ctypes.c_ulong),
        ("scheduling_class", ctypes.c_ulong),
    ]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("basic_limit_information", _BasicLimitInformation),
        ("io_info", _IoCounters),
        ("process_memory_limit", ctypes.c_size_t),
        ("job_memory_limit", ctypes.c_size_t),
        ("peak_process_memory_used", ctypes.c_size_t),
        ("peak_job_memory_used", ctypes.c_size_t),
    ]


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
    attach_child_to_job: Callable[[Any], int] | None = None,
    close_job: Callable[[int], None] | None = None,
) -> int:
    write_event = record or _append_watchdog_event
    attach = attach_child_to_job
    if attach is None and os.name == "nt":
        attach = _attach_child_to_kill_on_close_job
    close = close_job or _close_job_handle
    for restart_attempt in range(len(RESTART_DELAYS_SECONDS) + 1):
        child = popen(command, creationflags=CREATE_NO_WINDOW)
        job_handle: int | None = None
        if attach is not None:
            try:
                job_handle = attach(child)
            except OSError:
                _terminate_uncontained_child(child)
                write_event(
                    _watchdog_event(
                        "SUPERVISOR_CHILD_CONTAINMENT_FAILED",
                        child_pid=int(child.pid),
                        return_code=1,
                        restart_attempt=restart_attempt,
                        restart_delay_seconds=0,
                    )
                )
                return 1
        try:
            return_code = int(child.wait())
        finally:
            if job_handle is not None:
                close(job_handle)
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


def _attach_child_to_kill_on_close_job(child: Any) -> int:
    kernel = ctypes.windll.kernel32
    kernel.CreateJobObjectW.restype = ctypes.c_void_p
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError()
    job_handle = int(job)
    information = _ExtendedLimitInformation()
    information.basic_limit_information.limit_flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    configured = kernel.SetInformationJobObject(
        ctypes.c_void_p(job_handle),
        JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(information),
        ctypes.sizeof(information),
    )
    process_handle = int(getattr(child, "_handle", 0))
    assigned = process_handle and kernel.AssignProcessToJobObject(
        ctypes.c_void_p(job_handle),
        ctypes.c_void_p(process_handle),
    )
    if not configured or not assigned:
        kernel.CloseHandle(ctypes.c_void_p(job_handle))
        raise ctypes.WinError()
    return job_handle


def _close_job_handle(job_handle: int) -> None:
    ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(job_handle))


def _terminate_uncontained_child(child: Any) -> None:
    child.terminate()
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=5)


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
