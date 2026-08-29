"""Deterministic resource guard for Autonomous DEMO Operations RC2."""

from __future__ import annotations

from collections.abc import Mapping


MAX_HARDWARE_TEMPERATURE_C = 80.0
MINIMUM_MEMORY_AVAILABLE_MB = 512.0
MINIMUM_DISK_FREE_GB = 2.0

_GUARDRAILS = {
    "safe_to_trade": False,
    "real_trading": False,
    "execution_allowed": False,
}


def evaluate_resource_snapshot(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Evaluate observed host resources without guessing missing telemetry."""
    reasons: list[str] = []
    warnings: list[str] = []
    temperatures = _temperatures(snapshot)

    if snapshot.get("probe_status") != "OK":
        reasons.append("resource_probe_unavailable")
    if not temperatures:
        reasons.append("temperature_telemetry_unavailable")
    elif max(temperatures) >= MAX_HARDWARE_TEMPERATURE_C:
        reasons.append("thermal_guardrail_exceeded")
    if not _at_least(snapshot.get("memory_available_mb"), MINIMUM_MEMORY_AVAILABLE_MB):
        reasons.append("memory_guardrail_exceeded")
    if not _at_least(snapshot.get("disk_free_gb"), MINIMUM_DISK_FREE_GB):
        reasons.append("disk_guardrail_exceeded")
    if snapshot.get("wsl_running") is not True:
        reasons.append("wsl_runtime_unavailable")
    if snapshot.get("supervisor_logical_instances") != 1:
        reasons.append("supervisor_instance_count_invalid")

    cpu_temperatures = snapshot.get("cpu_temperatures_c")
    if not isinstance(cpu_temperatures, list) or not cpu_temperatures:
        warnings.append("cpu_temperature_telemetry_unavailable")
    if not isinstance(snapshot.get("process_handles"), int):
        warnings.append("process_handle_telemetry_unavailable")
    if not isinstance(snapshot.get("wsl_fd_soft_limit"), int):
        warnings.append("wsl_fd_telemetry_unavailable")
    if snapshot.get("wsl_telemetry_degraded") is True:
        warnings.append("wsl_resource_telemetry_degraded")

    status = "BLOCK" if reasons else "WARNING" if warnings else "OK"
    return {
        "schema": "odin.autonomous_demo_resources/v1",
        "status": status,
        "reason_codes": reasons,
        "warning_codes": warnings,
        "thermal_limit_c": MAX_HARDWARE_TEMPERATURE_C,
        "minimum_memory_available_mb": MINIMUM_MEMORY_AVAILABLE_MB,
        "minimum_disk_free_gb": MINIMUM_DISK_FREE_GB,
        "snapshot": dict(snapshot),
        **_GUARDRAILS,
    }


def parse_wsl_resource_snapshot(output: str) -> dict[str, object]:
    """Parse one bounded WSL sample without inventing missing metrics."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) < 3 or not lines[0].isdigit() or not lines[1].isdigit():
        return {
            "wsl_running": False,
            "wsl_probe_error_code": "wsl_resource_probe_invalid_output",
        }
    memory_line = next((line for line in lines[2:] if line.startswith("Mem:")), "")
    parts = memory_line.split()
    if len(parts) < 7 or not all(part.isdigit() for part in (parts[1], parts[6])):
        return {
            "wsl_running": False,
            "wsl_probe_error_code": "wsl_resource_probe_invalid_output",
        }
    result: dict[str, object] = {
        "wsl_running": True,
        "wsl_process_count": int(lines[1]),
        "wsl_fd_soft_limit": int(lines[0]),
        "wsl_memory_total_mb": round(int(parts[1]) / (1024 * 1024)),
        "wsl_memory_available_mb": round(int(parts[6]) / (1024 * 1024)),
    }
    hermes_line = next((line for line in lines[2:] if line.startswith("HERMES:")), "")
    if hermes_line in {"HERMES:0", "HERMES:1"}:
        result["wsl_hermes_running"] = hermes_line == "HERMES:1"
    for marker, key in (
        ("WSL_LOGS_BYTES:", "wsl_logs_bytes"),
        ("WSL_SQLITE_BYTES:", "wsl_sqlite_bytes"),
    ):
        line = next((item for item in lines[2:] if item.startswith(marker)), "")
        if not line:
            continue
        raw = line.removeprefix(marker)
        if not raw.isdigit():
            return {
                "wsl_running": False,
                "wsl_probe_error_code": "wsl_resource_probe_invalid_output",
            }
        result[key] = int(raw)
    return result


def merge_resource_storage_totals(
    host_snapshot: Mapping[str, object],
    wsl_snapshot: Mapping[str, object],
) -> dict[str, object]:
    """Merge exact WSL storage observations without hiding either source."""
    result = dict(host_snapshot)
    result.update(wsl_snapshot)
    for total_key, wsl_key in (
        ("logs_and_reports_bytes", "wsl_logs_bytes"),
        ("sqlite_bytes", "wsl_sqlite_bytes"),
    ):
        host_value = _byte_count(host_snapshot.get(total_key))
        wsl_value = _byte_count(wsl_snapshot.get(wsl_key))
        if host_value is None or wsl_value is None:
            continue
        result[f"windows_{total_key}"] = host_value
        result[total_key] = host_value + wsl_value
    return result


def _temperatures(snapshot: Mapping[str, object]) -> list[float]:
    values: list[float] = []
    gpu = snapshot.get("gpu_temperature_c")
    if isinstance(gpu, (int, float)):
        values.append(float(gpu))
    cpu = snapshot.get("cpu_temperatures_c")
    if isinstance(cpu, list):
        values.extend(float(value) for value in cpu if isinstance(value, (int, float)))
    return values


def _at_least(value: object, minimum: float) -> bool:
    return isinstance(value, (int, float)) and float(value) >= minimum


def _byte_count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return None
    return int(value)
