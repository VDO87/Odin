from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from odin_control.system_controller import SystemController
from odin_core.runtime_validator import validate_runtime_artifacts
from odin_core.safety_runtime_checks import run_runtime_safety_checks
from odin_logs.logger import JsonlLogger
from odin_logs.redaction import redact_sensitive_data


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bool_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() == "true"


def _safe_env_defaults() -> None:
    os.environ["ENABLE_REAL_TRADING"] = "false"
    os.environ["ENABLE_AUTO_EXECUTION"] = "false"
    os.environ["MT5_ORDER_SEND_ENABLED"] = "false"
    os.environ["XTB_REAL_ENABLED"] = "false"
    os.environ["BROKER_ALLOW_REAL_EXECUTION"] = "false"
    os.environ["OPENAI_SUPPORT_ENABLED"] = "false"


def _count_events(events_file: Path) -> int:
    if not events_file.exists():
        return 0
    return len(events_file.read_text(encoding="utf-8", errors="ignore").splitlines())


def _tail_events(events_file: Path, limit: int = 100) -> list[dict[str, Any]]:
    if not events_file.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in events_file.read_text(encoding="utf-8", errors="ignore").splitlines()[-max(1, limit) :]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _write_markdown_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cycles = payload.get("cycles", [])
    summary = payload.get("summary", {})
    dangerous = payload.get("dangerous_commands", [])
    errors = payload.get("errors", [])
    lines = [
        "# ODIN RC1.5 Soak Test Result",
        "",
        f"- Started at: `{payload.get('started_at')}`",
        f"- Finished at: `{payload.get('finished_at')}`",
        f"- Duration seconds: `{payload.get('duration_seconds')}`",
        f"- Result: `{summary.get('result')}`",
        "",
        "## Summary",
        f"- Total cycles: `{summary.get('total_cycles')}`",
        f"- Successful cycles: `{summary.get('successful_cycles')}`",
        f"- Failed cycles: `{summary.get('failed_cycles')}`",
        f"- Max cycle duration ms: `{summary.get('max_cycle_duration_ms')}`",
        f"- Avg cycle duration ms: `{summary.get('avg_cycle_duration_ms')}`",
        f"- Total errors: `{summary.get('total_errors')}`",
        f"- Heartbeat valid: `{summary.get('heartbeat_ok')}`",
        f"- Snapshot valid: `{summary.get('snapshot_ok')}`",
        f"- Events valid: `{summary.get('events_ok')}`",
        f"- No order attempts: `{summary.get('no_order_attempts')}`",
        f"- Safety flags OK: `{summary.get('safety_flags_ok')}`",
        "",
        "## Dangerous Commands",
    ]
    if dangerous:
        for item in dangerous:
            lines.append(
                f"- `{item.get('command')}` -> accepted=`{item.get('accepted')}` reason=`{item.get('reason')}`"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Errors"])
    if errors:
        for err in errors:
            lines.append(f"- `{err}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Last Cycle"])
    if cycles:
        last = cycles[-1]
        for key in [
            "cycle_number",
            "timestamp",
            "duration_ms",
            "runtime_state",
            "safe_to_trade",
            "health_status",
            "heartbeat_written",
            "snapshot_written",
            "event_count",
            "mt5_status",
            "llm_status",
            "atlas_status",
            "order_attempt_detected",
        ]:
            lines.append(f"- {key}: `{last.get(key)}`")
    else:
        lines.append("- no cycles recorded")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ODIN soak test runner")
    parser.add_argument("--duration-seconds", type=int, default=None)
    parser.add_argument("--cycles", type=int, default=None)
    parser.add_argument("--sleep-seconds", type=float, default=None)
    parser.add_argument("--offline-ok", action="store_true")
    parser.add_argument("--mini", action="store_true")
    parser.add_argument("--report", type=str, default="docs/reports/ODIN_RC1_5_SOAK_TEST_RESULT.md")
    parser.add_argument("--json-output", type=str, default="")
    parser.add_argument("--no-network-required", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _safe_env_defaults()

    default_duration = int(os.getenv("ODIN_SOAK_TEST_DEFAULT_DURATION_SECONDS", "300"))
    mini_duration = int(os.getenv("ODIN_SOAK_TEST_MINI_DURATION_SECONDS", "60"))
    default_sleep = float(os.getenv("ODIN_SOAK_TEST_CYCLE_SLEEP_SECONDS", "5"))
    max_errors = int(os.getenv("ODIN_SOAK_TEST_MAX_ERRORS", "3"))
    output_dir = Path(os.getenv("ODIN_SOAK_TEST_OUTPUT_DIR", "data/runtime/soak_tests"))
    output_dir.mkdir(parents=True, exist_ok=True)

    duration_seconds = args.duration_seconds if args.duration_seconds is not None else default_duration
    if args.mini:
        duration_seconds = mini_duration
    sleep_seconds = args.sleep_seconds if args.sleep_seconds is not None else default_sleep
    if sleep_seconds < 0:
        sleep_seconds = 0.0

    controller = SystemController(log_root="logs")
    soak_log = JsonlLogger("logs/system/soak_test.log")
    error_log = JsonlLogger("logs/errors/soak_test_errors.log")

    heartbeat_file = Path(os.getenv("ODIN_HEARTBEAT_FILE", "data/runtime/odin_heartbeat.json"))
    snapshot_file = Path(os.getenv("ODIN_STATE_SNAPSHOT_FILE", "data/runtime/odin_state_snapshot.json"))
    events_file = Path(os.getenv("ODIN_EVENTS_FILE", "data/runtime/odin_events.jsonl"))

    soak_log.write(
        "soak_test_started",
        {
            "duration_seconds": duration_seconds,
            "requested_cycles": args.cycles,
            "sleep_seconds": sleep_seconds,
            "offline_ok": args.offline_ok,
            "no_network_required": args.no_network_required,
        },
    )
    controller.execute("RUNTIME_START", actor="soak-test", role="system")

    dangerous_commands = [
        "ENABLE_REAL_TRADING",
        "MT5_ORDER_SEND",
        "DIRECT_ORDER_SEND",
        "BROKER_REAL_EXECUTION",
    ]
    dangerous_results: list[dict[str, Any]] = []
    for command in dangerous_commands:
        cmd_result = controller.execute(command, actor="soak-test", role="operator")
        dangerous_results.append(
            {
                "command": command,
                "accepted": cmd_result.get("accepted"),
                "reason": cmd_result.get("reason"),
            }
        )

    started_at = _utc_now()
    start_monotonic = time.monotonic()
    deadline = start_monotonic + max(1, duration_seconds)
    cycles: list[dict[str, Any]] = []
    runtime_events: list[dict[str, Any]] = []
    errors: list[str] = []
    failed_cycles = 0
    successful_cycles = 0
    order_attempt_detected = False
    max_cycle_duration_ms = 0.0
    total_cycle_duration_ms = 0.0
    cycle_number = 0

    while True:
        if args.cycles is not None and cycle_number >= max(1, args.cycles):
            break
        if args.cycles is None and time.monotonic() >= deadline:
            break

        cycle_number += 1
        t0 = time.monotonic()

        if cycle_number == 2:
            controller.execute("RUNTIME_PAUSE", actor="soak-test", role="operator")
        if cycle_number == 3:
            controller.execute("RUNTIME_RESUME", actor="soak-test", role="operator")

        status_res = controller.execute("RUNTIME_STATUS", actor="soak-test", role="system")
        once_res = controller.execute("RUNTIME_RUN_ONCE", actor="soak-test", role="system")
        snap_res = controller.execute("RUNTIME_SNAPSHOT", actor="soak-test", role="system")
        validator = validate_runtime_artifacts()
        safety = run_runtime_safety_checks()

        duration_ms = round((time.monotonic() - t0) * 1000, 2)
        max_cycle_duration_ms = max(max_cycle_duration_ms, duration_ms)
        total_cycle_duration_ms += duration_ms

        runtime_payload = status_res.get("data", {}).get("runtime", {})
        snapshot_payload = snap_res.get("data", {}).get("snapshot", {})
        health_status = str(snapshot_payload.get("health", {}).get("status", "UNKNOWN"))
        mt5_status = str(
            snapshot_payload.get("mt5", {}).get("data", {}).get("mt5", {}).get("status", "UNKNOWN")
        )
        llm_status = str(
            snapshot_payload.get("llm", {}).get("status", snapshot_payload.get("assistant", {}).get("status", "UNKNOWN"))
        )
        atlas_status = str(
            snapshot_payload.get("atlas", {}).get("status", snapshot_payload.get("atlas", {}).get("reason", "UNKNOWN"))
        )

        safety_checks = {item["check"]: item for item in safety.get("checks", [])}
        order_event_ok = safety_checks.get("verify_no_order_attempts_in_events", {}).get("passed", True)
        order_log_ok = safety_checks.get("verify_no_order_attempts_in_logs", {}).get("passed", True)
        if not order_event_ok or not order_log_ok:
            order_attempt_detected = True

        cycle_error_count = int(runtime_payload.get("consecutive_errors", 0))
        cycle_row = {
            "cycle_number": cycle_number,
            "timestamp": _utc_now(),
            "duration_ms": duration_ms,
            "runtime_state": runtime_payload.get("state", "UNKNOWN"),
            "safe_to_trade": bool(runtime_payload.get("safe_to_trade", False)),
            "health_status": health_status,
            "heartbeat_written": heartbeat_file.exists(),
            "snapshot_written": snapshot_file.exists(),
            "event_count": _count_events(events_file),
            "error_count": cycle_error_count,
            "mt5_status": mt5_status,
            "llm_status": llm_status,
            "atlas_status": atlas_status,
            "broker_real_enabled": _bool_env("BROKER_ALLOW_REAL_EXECUTION"),
            "mt5_order_send_enabled": _bool_env("MT5_ORDER_SEND_ENABLED"),
            "real_trading_enabled": _bool_env("ENABLE_REAL_TRADING"),
            "order_attempt_detected": order_attempt_detected,
            "validator_status": validator.get("status"),
            "safety_status": safety.get("status"),
        }
        cycles.append(cycle_row)
        runtime_events.append({"type": "SOAK_CYCLE", "payload": cycle_row})
        soak_log.write("soak_cycle", redact_sensitive_data(cycle_row))

        if once_res.get("accepted"):
            successful_cycles += 1
        else:
            failed_cycles += 1
            errors.append(f"cycle_{cycle_number}:{once_res.get('reason')}")
            error_log.write("soak_cycle_error", {"cycle": cycle_number, "reason": once_res.get("reason")})

        if validator.get("status") == "FAIL":
            failed_cycles += 1
            errors.append(f"cycle_{cycle_number}:runtime_validator_fail")

        if safety.get("status") == "FAIL":
            failed_cycles += 1
            errors.append(f"cycle_{cycle_number}:runtime_safety_fail")

        if order_attempt_detected:
            errors.append("critical:order_attempt_detected")
            break

        if len(errors) >= max_errors:
            break

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    controller.execute("RUNTIME_SAFE_SHUTDOWN", actor="soak-test", role="system")

    validator_final = validate_runtime_artifacts()
    safety_final = run_runtime_safety_checks()

    dangerous_blocked = all(
        (item.get("accepted") is False) and (str(item.get("reason")) in {"dangerous_command_blocked", "unsupported_command"})
        for item in dangerous_results
    )
    heartbeat_ok = validator_final.get("checks", [])[0]["status"] in {"PASS", "WARNING"} if validator_final.get("checks") else False
    snapshot_ok = validator_final.get("checks", [])[1]["status"] in {"PASS", "WARNING"} if validator_final.get("checks") else False
    events_ok = validator_final.get("checks", [])[2]["status"] in {"PASS", "WARNING"} if validator_final.get("checks") else False

    safety_flags_ok = all(
        item.get("passed", False)
        for item in safety_final.get("checks", [])
        if item.get("check")
        in {
            "verify_no_real_trading_enabled",
            "verify_mt5_order_send_disabled",
            "verify_xtb_real_disabled",
            "verify_broker_real_disabled",
            "verify_openai_disabled_by_default",
        }
    )

    total_cycles = len(cycles)
    avg_cycle_duration_ms = round(total_cycle_duration_ms / total_cycles, 2) if total_cycles else 0.0
    no_order_attempts = not order_attempt_detected

    result_status = "PASS"
    if not no_order_attempts or not dangerous_blocked:
        result_status = "FAIL"
    elif failed_cycles > 0 or validator_final.get("status") == "FAIL" or safety_final.get("status") == "FAIL":
        result_status = "WARNING"

    payload: dict[str, Any] = {
        "started_at": started_at,
        "finished_at": _utc_now(),
        "duration_seconds": round(time.monotonic() - start_monotonic, 2),
        "cycles": cycles,
        "dangerous_commands": dangerous_results,
        "errors": errors,
        "summary": {
            "total_cycles": total_cycles,
            "successful_cycles": successful_cycles,
            "failed_cycles": failed_cycles,
            "max_cycle_duration_ms": max_cycle_duration_ms,
            "avg_cycle_duration_ms": avg_cycle_duration_ms,
            "total_errors": len(errors),
            "heartbeat_ok": heartbeat_ok,
            "snapshot_ok": snapshot_ok,
            "events_ok": events_ok,
            "no_order_attempts": no_order_attempts,
            "safety_flags_ok": safety_flags_ok,
            "dangerous_commands_blocked": dangerous_blocked,
            "result": result_status,
        },
        "validator_final": validator_final,
        "safety_final": safety_final,
        "latest_events": _tail_events(events_file, 100),
    }

    latest_json = output_dir / "latest_soak_result.json"
    latest_events = output_dir / "latest_soak_events.jsonl"
    latest_json.write_text(json.dumps(redact_sensitive_data(payload), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    with latest_events.open("w", encoding="utf-8") as handle:
        latest_events_payload = payload.get("latest_events", [])
        if isinstance(latest_events_payload, list):
            for event in latest_events_payload:
                handle.write(json.dumps(redact_sensitive_data(event), sort_keys=True) + "\n")

    report_path = Path(args.report)
    _write_markdown_report(report_path, payload)
    if args.json_output:
        Path(args.json_output).write_text(
            json.dumps(redact_sensitive_data(payload), sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    soak_log.write("soak_test_finished", {"result": result_status, "summary": payload["summary"]})
    error_log.write(
        "soak_test_error_summary",
        {"total_errors": len(errors), "result": result_status, "errors": errors},
    )

    print(json.dumps({"result": result_status, "summary": payload["summary"]}, sort_keys=True))
    return 0 if result_status in {"PASS", "WARNING"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
