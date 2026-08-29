"""Bounded Windows resource snapshot for Autonomous DEMO RC2."""

from __future__ import annotations

import argparse
import csv
import ctypes
import json
from pathlib import Path
import shutil
import subprocess
import time


MUTEX_NAME = "Local\\ODIN_AUTONOMOUS_DEMO_RC2_SUPERVISOR"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class _FileTime(ctypes.Structure):
    _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]


class _MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_uint32),
        ("memory_load", ctypes.c_uint32),
        ("total_physical", ctypes.c_uint64),
        ("available_physical", ctypes.c_uint64),
        ("total_page_file", ctypes.c_uint64),
        ("available_page_file", ctypes.c_uint64),
        ("total_virtual", ctypes.c_uint64),
        ("available_virtual", ctypes.c_uint64),
        ("available_extended_virtual", ctypes.c_uint64),
    ]


class _ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_uint32),
        ("usage", ctypes.c_uint32),
        ("process_id", ctypes.c_uint32),
        ("default_heap_id", ctypes.POINTER(ctypes.c_ulong)),
        ("module_id", ctypes.c_uint32),
        ("threads", ctypes.c_uint32),
        ("parent_process_id", ctypes.c_uint32),
        ("priority_base", ctypes.c_long),
        ("flags", ctypes.c_uint32),
        ("executable", ctypes.c_wchar * 260),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supervisor-process-id", required=True, type=int)
    parser.add_argument("--root", default=r"D:\ODIN_LOCAL")
    arguments = parser.parse_args()

    memory_total_mb, memory_available_mb = _memory_megabytes()
    disk = shutil.disk_usage(arguments.root)
    gpu = _gpu_snapshot()
    processes = _process_names()
    mutex_verified = _mutex_exists(MUTEX_NAME)
    snapshot: dict[str, object] = {
        "schema": "odin.autonomous_demo_resource_snapshot/v1",
        "probe_status": "OK",
        "sampled_at_utc": _utc_now(),
        "cpu_load_percent": _cpu_load_percent(),
        "cpu_temperatures_c": [],
        "memory_total_mb": memory_total_mb,
        "memory_available_mb": memory_available_mb,
        **gpu,
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "process_handles": _process_handle_count(arguments.supervisor_process_id),
        "supervisor_processes": 1 if mutex_verified else 0,
        "supervisor_logical_instances": 1 if mutex_verified else 0,
        "supervisor_instance_basis": "named_mutex_verified" if mutex_verified else "missing",
        "wsl_running": None,
        "wsl_process_count": None,
        "wsl_fd_soft_limit": None,
        "wsl_memory_total_mb": None,
        "wsl_memory_available_mb": None,
        "logs_and_reports_bytes": _directory_bytes(
            Path(arguments.root) / "logs", Path(arguments.root) / "reports"
        ),
        "sqlite_bytes": _sqlite_bytes(Path(arguments.root) / "runtime"),
        "ollama_running": any(name in {"ollama.exe", "ollama app.exe"} for name in processes),
        "hermes_running": "hermes.exe" in processes,
    }
    print(json.dumps(snapshot, separators=(",", ":"), sort_keys=True))
    return 0


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _filetime_value(value: _FileTime) -> int:
    return (int(value.high) << 32) | int(value.low)


def _system_times() -> tuple[int, int, int]:
    idle = _FileTime()
    kernel = _FileTime()
    user = _FileTime()
    if not ctypes.windll.kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    ):
        raise OSError("windows_system_times_unavailable")
    return _filetime_value(idle), _filetime_value(kernel), _filetime_value(user)


def _cpu_load_percent() -> float | None:
    try:
        before = _system_times()
        time.sleep(0.1)
        after = _system_times()
        idle = after[0] - before[0]
        total = (after[1] - before[1]) + (after[2] - before[2])
        if total <= 0:
            return None
        return round(max(0.0, min(100.0, 100.0 * (total - idle) / total)), 1)
    except OSError:
        return None


def _memory_megabytes() -> tuple[int, int]:
    value = _MemoryStatus()
    value.length = ctypes.sizeof(_MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
        raise OSError("windows_memory_status_unavailable")
    return round(value.total_physical / (1024**2)), round(value.available_physical / (1024**2))


def _process_handle_count(process_id: int) -> int | None:
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_bool, ctypes.c_uint32)
    process = kernel.OpenProcess(0x1000, False, process_id)
    if not process:
        return None
    try:
        count = ctypes.c_uint32()
        if not kernel.GetProcessHandleCount(process, ctypes.byref(count)):
            return None
        return int(count.value)
    finally:
        kernel.CloseHandle(process)


def _mutex_exists(name: str) -> bool:
    kernel = ctypes.windll.kernel32
    kernel.OpenMutexW.restype = ctypes.c_void_p
    kernel.OpenMutexW.argtypes = (ctypes.c_uint32, ctypes.c_bool, ctypes.c_wchar_p)
    handle = kernel.OpenMutexW(0x00100000, False, name)
    if not handle:
        return False
    kernel.CloseHandle(handle)
    return True


def _gpu_snapshot() -> dict[str, object]:
    empty: dict[str, object] = {
        "gpu_name": None,
        "gpu_temperature_c": None,
        "gpu_utilization_percent": None,
        "gpu_memory_total_mb": None,
        "gpu_memory_used_mb": None,
    }
    executable = shutil.which("nvidia-smi.exe")
    if not executable:
        return empty
    try:
        completed = subprocess.run(
            [
                executable,
                "--query-gpu=name,temperature.gpu,utilization.gpu,memory.total,memory.used",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return empty
    if completed.returncode != 0:
        return empty
    try:
        row = next(csv.reader(completed.stdout.splitlines()))
        if len(row) != 5:
            return empty
        return {
            "gpu_name": row[0].strip(),
            "gpu_temperature_c": float(row[1]),
            "gpu_utilization_percent": float(row[2]),
            "gpu_memory_total_mb": float(row[3]),
            "gpu_memory_used_mb": float(row[4]),
        }
    except (StopIteration, ValueError):
        return empty


def _process_names() -> set[str]:
    kernel = ctypes.windll.kernel32
    kernel.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    snapshot = kernel.CreateToolhelp32Snapshot(0x00000002, 0)
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        return set()
    names: set[str] = set()
    entry = _ProcessEntry()
    entry.size = ctypes.sizeof(_ProcessEntry)
    try:
        available = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while available:
            names.add(str(entry.executable).casefold())
            available = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    return names


def _directory_bytes(*roots: Path) -> int:
    total = 0
    for root in roots:
        try:
            files = root.rglob("*")
            total += sum(path.stat().st_size for path in files if path.is_file())
        except OSError:
            continue
    return total


def _sqlite_bytes(root: Path) -> int:
    try:
        return sum(path.stat().st_size for path in root.glob("*.sqlite*") if path.is_file())
    except OSError:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
