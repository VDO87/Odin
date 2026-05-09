from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from odin_logs.logger import JsonlLogger


_DANGEROUS_ORDER_COMMANDS = {"DIRECT_ORDER_SEND", "MT5_ORDER_SEND", "MT5_CLOSE_POSITION", "MT5_MODIFY_POSITION", "BROKER_REAL_EXECUTION"}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _result(check: str, status: str, reason: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"check": check, "status": status, "reason": reason, "data": data or {}}


def _resolve_path(path: str | Path | None, env_name: str, default: str) -> Path:
    raw: str | Path
    if path is None:
        raw = os.getenv(env_name, default)
    else:
        raw = path
    return Path(raw)


def _contains_sensitive_text(text: str) -> bool:
    low = text.lower()
    markers = (
        "telegram_bot_token=",
        "openai_api_key=",
        "xtb_password=",
        "mt5_password=",
        "password=",
        "api_key=",
    )
    return any(marker in low for marker in markers)


def validate_heartbeat(path: str | Path | None = None) -> dict[str, Any]:
    heartbeat_path = _resolve_path(path, "ODIN_HEARTBEAT_FILE", "data/runtime/odin_heartbeat.json")
    if not heartbeat_path.exists():
        return _result("heartbeat", "FAIL", "heartbeat_missing", {"path": str(heartbeat_path)})
    try:
        payload = json.loads(heartbeat_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _result("heartbeat", "FAIL", "heartbeat_invalid_json", {"path": str(heartbeat_path)})
    timestamp = str(payload.get("timestamp", ""))
    parsed = _parse_iso_timestamp(timestamp)
    if parsed is None:
        return _result("heartbeat", "FAIL", "heartbeat_invalid_timestamp", {"timestamp": timestamp})
    age = (_now_utc() - parsed).total_seconds()
    if age > 600:
        return _result("heartbeat", "WARNING", "heartbeat_stale", {"age_seconds": age})
    if "runtime_state" not in payload:
        return _result("heartbeat", "FAIL", "heartbeat_missing_runtime_state")
    if _contains_sensitive_text(json.dumps(payload, sort_keys=True)):
        return _result("heartbeat", "FAIL", "heartbeat_sensitive_data_detected")
    return _result("heartbeat", "PASS", "heartbeat_valid", {"age_seconds": age})


def validate_snapshot(path: str | Path | None = None) -> dict[str, Any]:
    snapshot_path = _resolve_path(path, "ODIN_STATE_SNAPSHOT_FILE", "data/runtime/odin_state_snapshot.json")
    if not snapshot_path.exists():
        return _result("snapshot", "FAIL", "snapshot_missing", {"path": str(snapshot_path)})
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _result("snapshot", "FAIL", "snapshot_invalid_json", {"path": str(snapshot_path)})

    required = ("safe_to_trade", "trading_real_enabled", "mt5_order_send_enabled", "xtb_real_enabled", "broker_real_enabled", "last_events")
    missing = [name for name in required if name not in payload]
    if missing:
        return _result("snapshot", "FAIL", "snapshot_missing_fields", {"missing": missing})

    unsafe_flags = {
        "trading_real_enabled": bool(payload.get("trading_real_enabled", False)),
        "mt5_order_send_enabled": bool(payload.get("mt5_order_send_enabled", False)),
        "xtb_real_enabled": bool(payload.get("xtb_real_enabled", False)),
        "broker_real_enabled": bool(payload.get("broker_real_enabled", False)),
    }
    enabled = [name for name, value in unsafe_flags.items() if value]
    if enabled:
        return _result("snapshot", "FAIL", "snapshot_unsafe_flags_enabled", {"enabled": enabled})

    if _contains_sensitive_text(json.dumps(payload, sort_keys=True)):
        return _result("snapshot", "FAIL", "snapshot_sensitive_data_detected")

    return _result("snapshot", "PASS", "snapshot_valid")


def validate_events(path: str | Path | None = None) -> dict[str, Any]:
    events_path = _resolve_path(path, "ODIN_EVENTS_FILE", "data/runtime/odin_events.jsonl")
    if not events_path.exists():
        return _result("events", "FAIL", "events_missing", {"path": str(events_path)})

    lines = events_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not lines:
        return _result("events", "WARNING", "events_empty", {"path": str(events_path)})

    parsed_count = 0
    for line in lines[-200:]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return _result("events", "FAIL", "events_invalid_jsonl")
        if "timestamp" not in event or "event_type" not in event:
            return _result("events", "FAIL", "events_missing_fields")
        parsed_count += 1

    if _contains_sensitive_text("\n".join(lines[-200:])):
        return _result("events", "FAIL", "events_sensitive_data_detected")

    return _result("events", "PASS", "events_valid", {"validated_events": parsed_count})


def validate_runtime_logs() -> dict[str, Any]:
    expected = [
        Path("logs/system/runtime.log"),
        Path("logs/system/heartbeat.log"),
        Path("logs/system/events.log"),
    ]
    missing = [str(path) for path in expected if not path.exists()]
    if missing:
        return _result("logs", "WARNING", "runtime_logs_missing", {"missing": missing})

    for path in expected:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if _contains_sensitive_text(text):
            return _result("logs", "FAIL", "runtime_logs_sensitive_data_detected", {"path": str(path)})
        for line in text.splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            event = payload
            if str(payload.get("event_type", "")).lower() == "runtime_event":
                data = payload.get("data", {})
                if isinstance(data, dict):
                    event = data
            event_type = str(event.get("event_type", "")).upper()
            if event_type in {"ORDER_ATTEMPT", "ORDER_SENT", "BROKER_ORDER_REQUEST", "BROKER_ORDER_SENT"}:
                return _result("logs", "FAIL", "runtime_logs_order_send_detected", {"path": str(path)})
            if event_type == "COMMAND_RECEIVED":
                cmd = str(event.get("payload", {}).get("command", "")).upper()
                if cmd in _DANGEROUS_ORDER_COMMANDS:
                    return _result("logs", "FAIL", "runtime_logs_order_send_detected", {"path": str(path), "command": cmd})
    return _result("logs", "PASS", "runtime_logs_valid")


def validate_runtime_artifacts() -> dict[str, Any]:
    checks = [
        validate_heartbeat(),
        validate_snapshot(),
        validate_events(),
        validate_runtime_logs(),
    ]
    order = {"PASS": 0, "WARNING": 1, "FAIL": 2}
    worst = "PASS"
    for check in checks:
        if order[check["status"]] > order[worst]:
            worst = check["status"]
    result = "PASS" if worst == "PASS" else ("WARNING" if worst == "WARNING" else "FAIL")
    return {"status": result, "checks": checks}


def log_runtime_validation(result: dict[str, Any], *, log_path: str | Path = "logs/system/runtime_validation.log") -> None:
    JsonlLogger(log_path).write("runtime_validation", result)
