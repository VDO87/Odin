from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from odin_assistant.assistant_router import AssistantRouter
from odin_control.system_controller import SystemController
from odin_core.runtime_validator import validate_runtime_artifacts
from odin_dashboard.demo_state import get_demo_state
from odin_dashboard.security_badges import build_security_badges


_SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "login"}
_SPARKLINE_FALLBACK = [
    1.0818,
    1.08192,
    1.08202,
    1.08212,
    1.08205,
    1.08221,
    1.08214,
    1.08226,
    1.08218,
]


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


def _replace_none(payload: Any) -> Any:
    if payload is None:
        return "unavailable"
    if isinstance(payload, dict):
        return {str(key): _replace_none(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_replace_none(item) for item in payload]
    return payload


def _status_or(value: object, default: str = "unavailable") -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        return default
    return text.upper()


def _market_intelligence_demo_or_default(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    if snapshot and isinstance(snapshot.get("market_intelligence"), dict):
        return snapshot["market_intelligence"]
    return {
        "news_status": "UNAVAILABLE",
        "macro_calendar_status": "UNAVAILABLE",
        "sentiment_summary": "neutral",
        "high_impact_events": [],
        "blocked_by_news": False,
    }


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


def _risk_block_reasons(
    *,
    safe_to_trade: bool,
    health_state: str,
    mt5_state: str,
    runtime_validate_state: str,
    security: dict[str, bool | str],
) -> list[str]:
    reasons: list[str] = []
    if not safe_to_trade:
        if health_state in {"WARNING", "BLOCKED", "CRITICAL", "UNAVAILABLE"}:
            reasons.append(f"health={health_state}")
        if mt5_state in {"WARNING", "BLOCKED", "CRITICAL", "UNAVAILABLE"}:
            reasons.append(f"MT5={mt5_state}")
        if runtime_validate_state in {"WARNING", "BLOCKED", "CRITICAL", "UNAVAILABLE"}:
            reasons.append(f"runtime_validate={runtime_validate_state}")
        if bool(security.get("broker_real_blocked", False)):
            reasons.append("broker_real_blocked")
        if bool(security.get("mt5_order_send_blocked", False)):
            reasons.append("mt5_order_send_blocked")
        if bool(security.get("trading_real_blocked", False)):
            reasons.append("real_trading_disabled_by_policy")

    cleaned = []
    for reason in reasons:
        if "network_ok" in reason.lower():
            continue
        if reason not in cleaned:
            cleaned.append(reason)
    if not cleaned:
        return ["No active risk block detected"]
    return cleaned


class DashboardStateProvider:
    def __init__(self, *, log_root: str | Path = "logs") -> None:
        self.log_root = Path(log_root)
        self.snapshot_path = Path(os.getenv("ODIN_STATE_SNAPSHOT_FILE", "data/runtime/odin_state_snapshot.json"))
        self.heartbeat_path = Path(os.getenv("ODIN_HEARTBEAT_FILE", "data/runtime/odin_heartbeat.json"))
        self.events_path = Path(os.getenv("ODIN_EVENTS_FILE", "data/runtime/odin_events.jsonl"))
        self.soak_path = (
            Path(os.getenv("ODIN_SOAK_TEST_OUTPUT_DIR", "data/runtime/soak_tests")) / "latest_soak_result.json"
        )

    def _safe_controller_status(self) -> dict[str, Any]:
        try:
            controller = SystemController(log_root=self.log_root)
            assistant = AssistantRouter(controller)
            mt5 = controller.execute("MT5_STATUS", actor="dashboard:state", role="assistant")
            runtime = controller.execute("RUNTIME_STATUS", actor="dashboard:state", role="assistant")
            llm = assistant.llm_status()
            question = assistant.ask("Qual é o estado do ODIN?", channel="dashboard")
            return {"mt5": mt5, "runtime": runtime, "llm": llm, "assistant_last": question}
        except Exception as error:
            return {"status_error": f"{error.__class__.__name__}: {error}"}

    def _with_shared(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload["security_badges"] = build_security_badges()
        payload["install_paths"] = resolve_odin_home_paths()
        payload["atlas_profile"] = atlas_profile_status()
        payload["runtime_validate"] = validate_runtime_artifacts()
        return _replace_none(_sanitize(payload))

    def load_state(self, *, force_demo: bool = False) -> dict[str, Any]:
        if force_demo:
            return self._with_shared(get_demo_state())

        snapshot = _read_json(self.snapshot_path)
        heartbeat = _read_json(self.heartbeat_path)
        events = _read_jsonl_tail(self.events_path, limit=120)
        soak = _read_json(self.soak_path)

        if not snapshot:
            demo = get_demo_state()
            demo["note"] = "DEMO DATA: runtime snapshot indisponível"
            return self._with_shared(demo)

        control = self._safe_controller_status()
        runtime_validate = validate_runtime_artifacts()
        system_errors = _read_jsonl_tail(self.log_root / "errors" / "errors.log", limit=20)
        blocked_commands = _read_jsonl_tail(self.log_root / "assistant" / "blocked_requests.log", limit=20)

        mode = str(snapshot.get("odin_mode", os.getenv("ODIN_MODE", "SHADOW_MT5")))
        safe_to_trade = bool(snapshot.get("safe_to_trade", False))
        runtime_state = _status_or(snapshot.get("runtime_state"), "UNKNOWN")
        system_health_state = _status_or(snapshot.get("health", {}).get("status"), "UNAVAILABLE")
        trading_permission_state = "ALLOWED" if safe_to_trade else "BLOCKED"

        mt5_payload = snapshot.get("mt5", {}) if isinstance(snapshot.get("mt5"), dict) else {}
        mt5_data = (
            mt5_payload.get("data", {}).get("mt5", {}).get("data", {})
            if isinstance(mt5_payload.get("data"), dict)
            else {}
        )
        mt5_series = mt5_data.get("series", []) if isinstance(mt5_data.get("series"), list) else []
        mt5_status = _status_or(snapshot.get("mt5", {}).get("data", {}).get("mt5", {}).get("status"), "WARNING")
        use_demo_spark = not bool(mt5_series)
        if use_demo_spark:
            mt5_series = list(_SPARKLINE_FALLBACK)

        security: dict[str, bool | str] = {
            "trading_real_blocked": not bool(snapshot.get("trading_real_enabled", False)),
            "mt5_order_send_blocked": not bool(snapshot.get("mt5_order_send_enabled", False)),
            "broker_real_blocked": not bool(snapshot.get("broker_real_enabled", False)),
            "xtb_real_blocked": not bool(snapshot.get("xtb_real_enabled", False)),
            "atlas_execution": "SHADOW_ONLY",
            "llm_execution": "READ_ONLY",
        }
        runtime_validate_state = _status_or(runtime_validate.get("status"), "UNAVAILABLE")
        risk_reasons = _risk_block_reasons(
            safe_to_trade=safe_to_trade,
            health_state=system_health_state,
            mt5_state=mt5_status,
            runtime_validate_state=runtime_validate_state,
            security=security,
        )

        assistant_last = control.get("assistant_last", {}) if isinstance(control.get("assistant_last"), dict) else {}
        last_answer = assistant_last.get("answer", "No assistant response available")

        atlas = snapshot.get("atlas", {}) if isinstance(snapshot.get("atlas"), dict) else {}
        if "data_quality" not in atlas:
            atlas["data_quality"] = "fallback" if use_demo_spark else "active"
        for key in ["status", "profile", "execution_permission", "consensus"]:
            if key not in atlas or atlas.get(key) in ("", None):
                defaults = {
                    "status": "warning",
                    "profile": "lite",
                    "execution_permission": "SHADOW_ONLY",
                    "consensus": "unavailable",
                }
                atlas[key] = defaults[key]
        if isinstance(atlas.get("agents"), dict):
            for key in ["market_agent", "technical_agent", "news_agent", "risk_agent", "critic_agent"]:
                if atlas["agents"].get(key) in ("", None):
                    atlas["agents"][key] = "unavailable"
        else:
            atlas["agents"] = {
                "market_agent": "unavailable",
                "technical_agent": "unavailable",
                "news_agent": "unavailable",
                "risk_agent": "warning",
                "critic_agent": "warning",
            }

        state: dict[str, Any] = {
            "demo_data": False,
            "timestamp": snapshot.get("timestamp"),
            "mode": mode,
            "runtime_state": runtime_state,
            "trading_permission_state": trading_permission_state,
            "system_health_state": system_health_state,
            "safe_to_trade": safe_to_trade,
            "runtime": {
                "state": runtime_state,
                "trading_permission_state": trading_permission_state,
                "system_health_state": system_health_state,
                "safe_to_trade": safe_to_trade,
                "heartbeat": heartbeat.get("timestamp"),
                "health_status": system_health_state,
                "blocked_reasons": risk_reasons,
                "uptime_seconds": snapshot.get("uptime_seconds"),
                "runtime_validate": runtime_validate_state,
            },
            "security": security,
            "mt5": {
                "status": mt5_status,
                "raw": snapshot.get("mt5", {}),
                "positions": snapshot.get("positions", {}),
                "symbol": os.getenv("MT5_SYMBOLS", "EURUSD").split(",")[0].strip(),
                "timeframe": os.getenv("MT5_DEFAULT_TIMEFRAME", "M15"),
                "tick": mt5_data.get("tick", {}),
                "sparkline": mt5_series,
                "chart_label": "DEMO DATA" if use_demo_spark else "LIVE SNAPSHOT",
            },
            "market_intelligence": _market_intelligence_demo_or_default(snapshot),
            "atlas": atlas,
            "llm": snapshot.get("llm", {}),
            "risk": {
                "status": "ACTIVE",
                "engine": "REQUIRED",
                "max_risk_per_trade_percent": os.getenv("MAX_RISK_PER_TRADE_PERCENT", "0.25"),
                "max_daily_loss_percent": os.getenv("MAX_DAILY_LOSS_PERCENT", "1.00"),
                "max_trades_per_day": os.getenv("MAX_TRADES_PER_DAY", "5"),
                "trades_today": snapshot.get("trades_today", 0),
                "consecutive_losses": snapshot.get("consecutive_losses", 0),
                "blocked_reasons": risk_reasons,
                "safe_to_trade": safe_to_trade,
            },
            "broker_router": {
                "enabled": os.getenv("BROKER_ROUTER_ENABLED", "true").lower() == "true",
                "primary": os.getenv("BROKER_PRIMARY", "XTB"),
                "allow_real_execution": os.getenv("BROKER_ALLOW_REAL_EXECUTION", "false").lower() == "true",
            },
            "positions": snapshot.get("positions", {}),
            "assistant": {
                "last_question": assistant_last.get("question", "n/a"),
                "last_answer": last_answer,
                "source": assistant_last.get("source", "fallback"),
            },
            "events": events,
            "errors": system_errors,
            "blocked_commands": blocked_commands,
            "soak": soak.get("summary", soak),
            "controller": control,
        }
        return self._with_shared(state)
