from __future__ import annotations

import os
import re
import json
from pathlib import Path
from typing import Any


_DANGEROUS_ORDER_COMMANDS = {
    "DIRECT_ORDER_SEND",
    "MT5_ORDER_SEND",
    "MT5_CLOSE_POSITION",
    "MT5_MODIFY_POSITION",
    "BROKER_REAL_EXECUTION",
}
_ORDER_EVENT_TYPES = {
    "ORDER_ATTEMPT",
    "ORDER_SENT",
    "BROKER_ORDER_REQUEST",
    "BROKER_ORDER_SENT",
    "DIRECT_ORDER_SEND",
    "MT5_ORDER_SEND",
}

_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)telegram_bot_token\s*=\s*[^\s]+"),
    re.compile(r"(?i)openai_api_key\s*=\s*[^\s]+"),
    re.compile(r"(?i)xtb_password\s*=\s*[^\s]+"),
    re.compile(r"(?i)mt5_password\s*=\s*[^\s]+"),
    re.compile(r"(?i)password\s*[:=]\s*[^\s]+"),
    re.compile(r"\bsk-[A-Za-z0-9]{8,}\b"),
)


def _env_is_false(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"false", "0", "no", "off", ""}


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_json_lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            out.append(parsed)
    return out


def _result(check: str, passed: bool, details: str, *, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "check": check,
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "details": details,
        "data": data or {},
    }


def verify_no_real_trading_enabled() -> dict[str, Any]:
    passed = _env_is_false("ENABLE_REAL_TRADING")
    return _result(
        "verify_no_real_trading_enabled",
        passed,
        "ENABLE_REAL_TRADING=false" if passed else "ENABLE_REAL_TRADING=true detectado",
    )


def verify_mt5_order_send_disabled() -> dict[str, Any]:
    passed = _env_is_false("MT5_ORDER_SEND_ENABLED") and _env_is_false("ENABLE_MT5_ORDER_SEND")
    return _result(
        "verify_mt5_order_send_disabled",
        passed,
        "MT5 order_send desactivado" if passed else "MT5 order_send activado detectado",
    )


def verify_xtb_real_disabled() -> dict[str, Any]:
    passed = _env_is_false("XTB_REAL_ENABLED") and _env_is_false("ENABLE_XTB_REAL")
    return _result(
        "verify_xtb_real_disabled",
        passed,
        "XTB real desactivado" if passed else "XTB real activado detectado",
    )


def verify_broker_real_disabled() -> dict[str, Any]:
    passed = _env_is_false("BROKER_ALLOW_REAL_EXECUTION")
    return _result(
        "verify_broker_real_disabled",
        passed,
        "Broker real desactivado" if passed else "Broker real activado detectado",
    )


def verify_openai_disabled_by_default() -> dict[str, Any]:
    passed = _env_is_false("OPENAI_SUPPORT_ENABLED")
    return _result(
        "verify_openai_disabled_by_default",
        passed,
        "OpenAI suporte desligado por defeito" if passed else "OPENAI_SUPPORT_ENABLED=true detectado",
    )


def _is_order_attempt_event(event: dict[str, Any]) -> bool:
    event_type = str(event.get("event_type", "")).upper()
    if event_type in _ORDER_EVENT_TYPES:
        return True
    if event_type == "COMMAND_RECEIVED":
        payload = event.get("payload", {})
        if isinstance(payload, dict):
            return str(payload.get("command", "")).upper() in _DANGEROUS_ORDER_COMMANDS
    return False


def _extract_runtime_event(record: dict[str, Any]) -> dict[str, Any]:
    if str(record.get("event_type", "")).lower() == "runtime_event":
        data = record.get("data")
        if isinstance(data, dict):
            return data
    return record


def verify_no_order_attempts_in_events() -> dict[str, Any]:
    events_path = Path(os.getenv("ODIN_EVENTS_FILE", "data/runtime/odin_events.jsonl"))
    records = _read_json_lines(events_path)
    hits: list[str] = []
    for item in records:
        if _is_order_attempt_event(item):
            hits.append(str(item.get("event_type", "UNKNOWN")))
    passed = len(hits) == 0
    return _result(
        "verify_no_order_attempts_in_events",
        passed,
        "Sem tentativas de ordem em eventos" if passed else "Tentativas de ordem detectadas em eventos",
        data={"events_file": str(events_path), "matches": hits, "records": len(records)},
    )


def verify_no_order_attempts_in_logs() -> dict[str, Any]:
    candidates = [
        Path("logs/system/events.log"),
        Path("logs/trading/execution_audit.log"),
        Path("logs/brokers/requests.log"),
        Path("logs/control/commands.log"),
    ]
    matches: dict[str, list[str]] = {}
    for path in candidates:
        hits: list[str] = []
        for item in _read_json_lines(path):
            event = _extract_runtime_event(item)
            if _is_order_attempt_event(event):
                hits.append(str(event.get("event_type", "UNKNOWN")))
        if hits:
            matches[str(path)] = hits
    passed = not matches
    return _result(
        "verify_no_order_attempts_in_logs",
        passed,
        "Sem tentativas de ordem nos logs" if passed else "Tentativas de ordem detectadas em logs",
        data={"matches": matches},
    )


def verify_sensitive_data_redacted() -> dict[str, Any]:
    candidates = [
        Path("data/runtime/odin_state_snapshot.json"),
        Path("data/runtime/odin_events.jsonl"),
        Path("logs/system/events.log"),
        Path("logs/system/runtime.log"),
        Path("logs/assistant/llm_prompts.log"),
        Path("logs/assistant/llm_responses.log"),
    ]
    leaked: dict[str, list[str]] = {}
    for path in candidates:
        text = _read_text(path)
        if not text:
            continue
        path_hits: list[str] = []
        for pattern in _SENSITIVE_PATTERNS:
            if pattern.search(text):
                path_hits.append(pattern.pattern)
        if path_hits:
            leaked[str(path)] = path_hits
    passed = not leaked
    return _result(
        "verify_sensitive_data_redacted",
        passed,
        "Sem segredos detectados" if passed else "Padrões sensíveis detectados em logs/snapshots",
        data={"leaks": leaked},
    )


def run_runtime_safety_checks() -> dict[str, Any]:
    checks = [
        verify_no_real_trading_enabled(),
        verify_mt5_order_send_disabled(),
        verify_xtb_real_disabled(),
        verify_broker_real_disabled(),
        verify_openai_disabled_by_default(),
        verify_no_order_attempts_in_events(),
        verify_no_order_attempts_in_logs(),
        verify_sensitive_data_redacted(),
    ]
    passed = all(item["passed"] for item in checks)
    return {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "safe_to_trade": False,
    }
