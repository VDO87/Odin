from __future__ import annotations

import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from odin_assistant.redaction import redact_for_assistant
from odin_health.healthcheck import OdinHealthcheck


@dataclass(slots=True)
class AssistantContext:
    payload: dict[str, Any]


class ContextBuilder:
    def __init__(
        self,
        providers: dict[str, Callable[[], dict[str, Any]]] | None = None,
        *,
        log_root: str | Path = "logs",
    ) -> None:
        self.providers = providers or {}
        self.log_root = Path(log_root)

    @classmethod
    def from_controller(cls, controller: Any, *, log_root: str | Path = "logs") -> "ContextBuilder":
        def _call(command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
            return controller.execute(
                command,
                actor="assistant:context",
                role="assistant",
                payload=payload or {},
            )

        providers: dict[str, Callable[[], dict[str, Any]]] = {
            "mode": lambda: {
                "odin_mode": os.getenv("ODIN_MODE", "SHADOW_MT5"),
                "real_trading_enabled": os.getenv("ENABLE_REAL_TRADING", "false").lower() == "true",
            },
            "status": lambda: {"state": controller.machine.state.value},
            "can_operate": lambda: {
                "can_operate": controller.machine.state.value in {"READY", "RUNNING"},
                "state": controller.machine.state.value,
            },
            "healthcheck": lambda: OdinHealthcheck(log_root=log_root).run(),
            "network": lambda: OdinHealthcheck(log_root=log_root).run().get("checks", {}).get("network", {}),
            "mt5": lambda: _call("MT5_STATUS"),
            "mt5_health": lambda: _call("MT5_HEALTHCHECK"),
            "mt5_positions": lambda: _call("MT5_LIST_POSITIONS"),
            "mt5_reconciliation": lambda: _call("MT5_SYNC_POSITIONS"),
            "risk": lambda: {
                "risk_engine_required": True,
                "risk_engine_active": True,
                "max_risk_per_trade_percent": os.getenv("MAX_RISK_PER_TRADE_PERCENT", "0.25"),
            },
            "atlas": lambda: {
                "enabled": os.getenv("ATLAS_ENABLED", "true").lower() == "true",
                "mode": os.getenv("ATLAS_MODE", "CONSENSUS_ONLY"),
                "allow_direct_execution": os.getenv("ATLAS_ALLOW_DIRECT_EXECUTION", "false").lower() == "true",
            },
            "broker_router": lambda: {
                "enabled": os.getenv("BROKER_ROUTER_ENABLED", "true").lower() == "true",
                "allow_real_execution": os.getenv("BROKER_ALLOW_REAL_EXECUTION", "false").lower() == "true",
                "primary": os.getenv("BROKER_PRIMARY", "XTB"),
            },
            "security": lambda: {
                "trading_real_blocked": os.getenv("ENABLE_REAL_TRADING", "false").lower() != "true",
                "mt5_order_send_blocked": os.getenv("MT5_ORDER_SEND_ENABLED", "false").lower() != "true",
                "xtb_real_blocked": os.getenv("XTB_REAL_ENABLED", "false").lower() != "true",
                "broker_real_blocked": os.getenv("BROKER_ALLOW_REAL_EXECUTION", "false").lower() != "true",
            },
            "last_error": lambda: cls._read_last_error(log_root),
            "runtime": lambda: _call("RUNTIME_STATUS"),
            "runtime_snapshot": lambda: _call("RUNTIME_SNAPSHOT"),
            "runtime_events": lambda: cls._read_runtime_events(),
            "runtime_heartbeat": lambda: cls._read_runtime_heartbeat(),
            "runtime_soak": lambda: cls._runtime_soak_readiness(_call("RUNTIME_STATUS"), _call("MT5_STATUS"), OdinHealthcheck(log_root=log_root).run()),
            "signals": lambda: {"active_signals": []},
            "news": lambda: {"status": "not_configured"},
            "fire": lambda: {"status": "monitoring"},
            "blocked_signals": lambda: {"last_blocked": []},
        }
        return cls(providers, log_root=log_root)

    @staticmethod
    def _read_last_error(log_root: str | Path) -> dict[str, Any]:
        candidates = [
            Path(log_root) / "errors" / "errors.log",
            Path(log_root) / "system" / "errors.log",
        ]
        for path in candidates:
            if not path.exists():
                continue
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if lines:
                return {"path": str(path), "last_error": lines[-1][:800]}
        return {"last_error": None}

    @staticmethod
    def _read_runtime_heartbeat() -> dict[str, Any]:
        path = Path(os.getenv("ODIN_HEARTBEAT_FILE", "data/runtime/odin_heartbeat.json"))
        if not path.exists():
            return {"status": "missing_heartbeat"}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"status": "invalid_heartbeat"}

    @staticmethod
    def _read_runtime_events(limit: int = 20) -> dict[str, Any]:
        path = Path(os.getenv("ODIN_EVENTS_FILE", "data/runtime/odin_events.jsonl"))
        if not path.exists():
            return {"events": [], "status": "missing_events"}
        events: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-max(1, limit) :]:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return {"events": events, "count": len(events)}

    @staticmethod
    def _runtime_soak_readiness(runtime: dict[str, Any], mt5: dict[str, Any], health: dict[str, Any]) -> dict[str, Any]:
        runtime_state = str(runtime.get("data", {}).get("runtime", {}).get("state", "UNKNOWN"))
        mt5_status = str(mt5.get("data", {}).get("mt5", {}).get("status", "WARNING"))
        health_status = str(health.get("status", "WARNING"))
        ready = runtime_state in {"RUNNING", "DEGRADED"} and health_status in {"OK", "WARNING"} and mt5_status in {"OK", "WARNING", "BLOCKED"}
        return {
            "ready_for_soak_test": ready,
            "runtime_state": runtime_state,
            "mt5_status": mt5_status,
            "health_status": health_status,
        }

    def build(self) -> AssistantContext:
        data: dict[str, Any] = {}
        for name, provider in self.providers.items():
            try:
                data[name] = provider()
            except Exception as error:
                data[name] = {"error": f"{error.__class__.__name__}: {error}"}
        return AssistantContext(payload=redact_for_assistant(data))

    def build_for_question(self, question: str) -> AssistantContext:
        base = self.build().payload
        q = question.lower().strip()

        if "estado do odin" in q:
            return AssistantContext(
                payload={
                    "mode": base.get("mode", {}),
                    "status": base.get("status", {}),
                    "healthcheck": base.get("healthcheck", {}),
                    "network": base.get("network", {}),
                    "mt5": base.get("mt5", {}),
                    "risk": base.get("risk", {}),
                    "atlas": base.get("atlas", {}),
                    "broker_router": base.get("broker_router", {}),
                    "security": base.get("security", {}),
                    "last_error": base.get("last_error", {}),
                }
            )

        if "pode operar" in q:
            mt5_rec = base.get("mt5_reconciliation", {})
            return AssistantContext(
                payload={
                    "status": base.get("status", {}),
                    "can_operate": base.get("can_operate", {}),
                    "network": base.get("network", {}),
                    "mt5": base.get("mt5", {}),
                    "mt5_reconciliation": mt5_rec,
                    "risk": base.get("risk", {}),
                    "mode": base.get("mode", {}),
                    "broker_router": base.get("broker_router", {}),
                    "security": base.get("security", {}),
                }
            )

        if "runtime" in q or "heartbeat" in q or "snapshot" in q or "evento" in q or "soak" in q:
            return AssistantContext(
                payload={
                    "runtime": base.get("runtime", {}),
                    "runtime_snapshot": base.get("runtime_snapshot", {}),
                    "runtime_events": base.get("runtime_events", {}),
                    "runtime_heartbeat": base.get("runtime_heartbeat", {}),
                    "runtime_soak": base.get("runtime_soak", {}),
                    "healthcheck": base.get("healthcheck", {}),
                    "mt5": base.get("mt5", {}),
                    "atlas": base.get("atlas", {}),
                }
            )

        return AssistantContext(payload=base)
