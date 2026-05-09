from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from odin_assistant.assistant_router import AssistantRouter
from odin_control.system_controller import SystemController
from odin_dashboard.demo_state import get_demo_state
from odin_dashboard.security_badges import build_security_badges


_SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "login"}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        return {}
    return {}


def _read_jsonl_tail(path: Path, limit: int = 40) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-max(1, limit) :]:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _sanitize(payload: Any) -> Any:
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, value in payload.items():
            low = str(key).lower()
            if any(secret in low for secret in _SENSITIVE_KEYS):
                out[str(key)] = "***REDACTED***"
            else:
                out[str(key)] = _sanitize(value)
        return out
    if isinstance(payload, list):
        return [_sanitize(item) for item in payload]
    return payload


def resolve_odin_home_paths() -> dict[str, str]:
    odin_home = os.path.expandvars(os.getenv("ODIN_HOME", "/home/vdo/ODIN_RUNTIME"))
    mapping = {
        "ODIN_HOME": odin_home,
        "ODIN_APP_DIR": os.path.expandvars(os.getenv("ODIN_APP_DIR", f"{odin_home}/app")),
        "ODIN_CONFIG_DIR": os.path.expandvars(os.getenv("ODIN_CONFIG_DIR", f"{odin_home}/config")),
        "ODIN_DATA_DIR": os.path.expandvars(os.getenv("ODIN_DATA_DIR", f"{odin_home}/data")),
        "ODIN_LOG_DIR": os.path.expandvars(os.getenv("ODIN_LOG_DIR", f"{odin_home}/logs")),
        "ODIN_MODELS_DIR": os.path.expandvars(os.getenv("ODIN_MODELS_DIR", f"{odin_home}/models")),
        "ODIN_VENDOR_DIR": os.path.expandvars(os.getenv("ODIN_VENDOR_DIR", f"{odin_home}/vendor")),
        "ODIN_BACKUP_DIR": os.path.expandvars(os.getenv("ODIN_BACKUP_DIR", f"{odin_home}/backups")),
        "ODIN_TMP_DIR": os.path.expandvars(os.getenv("ODIN_TMP_DIR", f"{odin_home}/tmp")),
        "ODIN_DASHBOARD_PREVIEW_DIR": os.path.expandvars(
            os.getenv("ODIN_DASHBOARD_PREVIEW_DIR", f"{odin_home}/dashboard_preview")
        ),
    }
    return mapping


def atlas_profile_status() -> dict[str, object]:
    profile = os.getenv("ATLAS_PROFILE", os.getenv("ATLAS_DEFAULT_PROFILE", "lite")).strip().lower()
    accepted = profile in {"lite", "full"}
    if not accepted:
        profile = "lite"
    return {
        "profile": profile,
        "accepted": accepted,
        "lite_enabled": os.getenv("ATLAS_LITE_ENABLED", "true").lower() == "true",
        "full_enabled": os.getenv("ATLAS_FULL_ENABLED", "true").lower() == "true",
        "lite_max_agents": int(os.getenv("ATLAS_LITE_MAX_AGENTS", "4")),
        "full_max_agents": int(os.getenv("ATLAS_FULL_MAX_AGENTS", "9")),
        "execution_permission": "SHADOW_ONLY",
    }


class DashboardStateProvider:
    def __init__(self, *, log_root: str | Path = "logs") -> None:
        self.log_root = Path(log_root)
        self.snapshot_path = Path(os.getenv("ODIN_STATE_SNAPSHOT_FILE", "data/runtime/odin_state_snapshot.json"))
        self.heartbeat_path = Path(os.getenv("ODIN_HEARTBEAT_FILE", "data/runtime/odin_heartbeat.json"))
        self.events_path = Path(os.getenv("ODIN_EVENTS_FILE", "data/runtime/odin_events.jsonl"))
        self.soak_path = Path(os.getenv("ODIN_SOAK_TEST_OUTPUT_DIR", "data/runtime/soak_tests")) / "latest_soak_result.json"

    def _safe_controller_status(self) -> dict[str, Any]:
        try:
            controller = SystemController(log_root=self.log_root)
            assistant = AssistantRouter(controller)
            mt5 = controller.execute("MT5_STATUS", actor="dashboard:state", role="assistant")
            atlas = controller.execute("RUNTIME_STATUS", actor="dashboard:state", role="assistant")
            return {
                "mt5": mt5,
                "runtime": atlas,
                "llm": assistant.llm_status(),
                "assistant_last": assistant.ask("Qual é o estado do ODIN?", channel="dashboard"),
            }
        except Exception as error:
            return {"status_error": f"{error.__class__.__name__}: {error}"}

    def load_state(self, *, force_demo: bool = False) -> dict[str, Any]:
        if force_demo:
            demo = get_demo_state()
            demo["security_badges"] = build_security_badges()
            demo["install_paths"] = resolve_odin_home_paths()
            demo["atlas_profile"] = atlas_profile_status()
            return _sanitize(demo)

        snapshot = _read_json(self.snapshot_path)
        heartbeat = _read_json(self.heartbeat_path)
        events = _read_jsonl_tail(self.events_path, limit=50)
        soak = _read_json(self.soak_path)

        if not snapshot:
            demo = get_demo_state()
            demo["note"] = "DEMO DATA: runtime snapshot indisponível"
            demo["security_badges"] = build_security_badges()
            demo["install_paths"] = resolve_odin_home_paths()
            demo["atlas_profile"] = atlas_profile_status()
            return _sanitize(demo)

        control = self._safe_controller_status()
        system_errors = _read_jsonl_tail(self.log_root / "errors" / "errors.log", limit=20)
        blocked_commands = _read_jsonl_tail(self.log_root / "assistant" / "blocked_requests.log", limit=20)

        state: dict[str, Any] = {
            "demo_data": False,
            "timestamp": snapshot.get("timestamp"),
            "mode": snapshot.get("odin_mode", os.getenv("ODIN_MODE", "SHADOW_MT5")),
            "runtime": {
                "state": snapshot.get("runtime_state", "UNKNOWN"),
                "safe_to_trade": bool(snapshot.get("safe_to_trade", False)),
                "heartbeat": heartbeat.get("timestamp"),
                "health_status": snapshot.get("health", {}).get("status", "UNKNOWN"),
                "blocked_reasons": snapshot.get("health", {}).get("checks", {}).get("runtime", {}).get("reason", ""),
            },
            "security": {
                "trading_real_blocked": not bool(snapshot.get("trading_real_enabled", False)),
                "mt5_order_send_blocked": not bool(snapshot.get("mt5_order_send_enabled", False)),
                "broker_real_blocked": not bool(snapshot.get("broker_real_enabled", False)),
                "xtb_real_blocked": not bool(snapshot.get("xtb_real_enabled", False)),
                "atlas_execution": "SHADOW_ONLY",
                "llm_execution": "READ_ONLY",
            },
            "mt5": {
                "status": snapshot.get("mt5", {}).get("data", {}).get("mt5", {}).get("status", "WARNING"),
                "raw": snapshot.get("mt5", {}),
                "positions": snapshot.get("positions", {}),
            },
            "atlas": snapshot.get("atlas", {}),
            "llm": snapshot.get("llm", {}),
            "risk": snapshot.get("risk", {}),
            "broker_router": {
                "enabled": os.getenv("BROKER_ROUTER_ENABLED", "true").lower() == "true",
                "primary": os.getenv("BROKER_PRIMARY", "XTB"),
                "allow_real_execution": os.getenv("BROKER_ALLOW_REAL_EXECUTION", "false").lower() == "true",
            },
            "positions": snapshot.get("positions", {}),
            "assistant": snapshot.get("assistant", {}),
            "events": events,
            "errors": system_errors,
            "blocked_commands": blocked_commands,
            "soak": soak.get("summary", soak),
            "atlas_profile": atlas_profile_status(),
            "controller": control,
            "security_badges": build_security_badges(),
            "install_paths": resolve_odin_home_paths(),
        }
        return _sanitize(state)
