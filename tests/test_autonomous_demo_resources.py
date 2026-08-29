from __future__ import annotations

import pytest

from odin.trading.autonomous_demo_resources import (
    evaluate_resource_snapshot,
    parse_wsl_resource_snapshot,
)


def _snapshot(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "probe_status": "OK",
        "cpu_temperatures_c": [],
        "gpu_temperature_c": 39.0,
        "memory_available_mb": 5_800.0,
        "disk_free_gb": 230.0,
        "wsl_running": True,
        "supervisor_logical_instances": 1,
        "process_handles": 180,
        "wsl_fd_soft_limit": 10_240,
    }
    value.update(changes)
    return value


def test_live_shape_is_eligible_with_explicit_cpu_sensor_warning() -> None:
    result = evaluate_resource_snapshot(_snapshot())

    assert result["status"] == "WARNING"
    assert result["reason_codes"] == []
    assert result["warning_codes"] == ["cpu_temperature_telemetry_unavailable"]
    assert result["thermal_limit_c"] == 80.0
    assert result["execution_allowed"] is False
    assert result["real_trading"] is False


@pytest.mark.parametrize("temperature", [80.0, 91.0])
def test_hardware_at_or_above_thermal_limit_blocks(temperature: float) -> None:
    result = evaluate_resource_snapshot(_snapshot(gpu_temperature_c=temperature))

    assert result["status"] == "BLOCK"
    assert "thermal_guardrail_exceeded" in result["reason_codes"]


def test_missing_all_temperature_telemetry_blocks_without_invention() -> None:
    result = evaluate_resource_snapshot(
        _snapshot(gpu_temperature_c=None, cpu_temperatures_c=[])
    )

    assert result["status"] == "BLOCK"
    assert "temperature_telemetry_unavailable" in result["reason_codes"]


def test_combined_wsl_resource_sample_is_parsed_deterministically() -> None:
    result = parse_wsl_resource_snapshot(
        "10240\n39\n"
        "               total        used        free      shared  buff/cache   available\n"
        "Mem:      8589934592  2147483648  1073741824  0  5368709120  6442450944\n"
    )

    assert result == {
        "wsl_running": True,
        "wsl_process_count": 39,
        "wsl_fd_soft_limit": 10240,
        "wsl_memory_total_mb": 8192,
        "wsl_memory_available_mb": 6144,
    }


def test_invalid_wsl_resource_sample_fails_closed_without_fake_metrics() -> None:
    result = parse_wsl_resource_snapshot("partial output")

    assert result == {
        "wsl_running": False,
        "wsl_probe_error_code": "wsl_resource_probe_invalid_output",
    }


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"probe_status": "BLOCKED"}, "resource_probe_unavailable"),
        ({"memory_available_mb": 511.0}, "memory_guardrail_exceeded"),
        ({"disk_free_gb": 1.99}, "disk_guardrail_exceeded"),
        ({"wsl_running": False}, "wsl_runtime_unavailable"),
        ({"supervisor_logical_instances": 2}, "supervisor_instance_count_invalid"),
    ],
)
def test_resource_failure_modes_fail_closed(
    changes: dict[str, object], reason: str
) -> None:
    result = evaluate_resource_snapshot(_snapshot(**changes))

    assert result["status"] == "BLOCK"
    assert reason in result["reason_codes"]
    assert result["safe_to_trade"] is False
    assert result["execution_allowed"] is False
