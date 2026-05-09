from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from odin_assistant.assistant_router import AssistantRouter
from odin_atlas.coordinator import AtlasCoordinator
from odin_core.events import RuntimeEventLog
from odin_core.heartbeat import HeartbeatWriter
from odin_core.runtime_state import RuntimeState, RuntimeStatus, now_iso
from odin_health.healthcheck import OdinHealthcheck
from odin_logs.logger import JsonlLogger
from odin_logs.redaction import redact_sensitive_data


class ShadowRuntimeOrchestrator:
    def __init__(self, controller: Any, *, log_root: str | Path = "logs") -> None:
        self.controller = controller
        self.log_root = Path(log_root)
        self.data_root = Path("data/runtime")
        self.data_root.mkdir(parents=True, exist_ok=True)

        self.runtime_enabled = os.getenv("ODIN_RUNTIME_ENABLED", "true").lower() == "true"
        self.runtime_mode = os.getenv("ODIN_RUNTIME_MODE", "SHADOW")
        self.heartbeat_seconds = int(os.getenv("ODIN_RUNTIME_HEARTBEAT_SECONDS", "10"))
        self.healthcheck_seconds = int(os.getenv("ODIN_RUNTIME_HEALTHCHECK_SECONDS", "60"))
        self.mt5_poll_seconds = int(os.getenv("ODIN_RUNTIME_MT5_POLL_SECONDS", "15"))
        self.atlas_cycle_seconds = int(os.getenv("ODIN_RUNTIME_ATLAS_CYCLE_SECONDS", "60"))
        self.assistant_context_seconds = int(os.getenv("ODIN_RUNTIME_ASSISTANT_CONTEXT_SECONDS", "30"))
        self.max_cycle_errors = int(os.getenv("ODIN_RUNTIME_MAX_CYCLE_ERRORS", "3"))
        self.auto_recovery = os.getenv("ODIN_RUNTIME_AUTO_RECOVERY", "true").lower() == "true"
        self.stop_on_critical = os.getenv("ODIN_RUNTIME_STOP_ON_CRITICAL", "true").lower() == "true"
        self.safe_shutdown_timeout_seconds = int(
            os.getenv("ODIN_RUNTIME_SAFE_SHUTDOWN_TIMEOUT_SECONDS", "15")
        )

        self.snapshot_file = Path(
            os.getenv("ODIN_STATE_SNAPSHOT_FILE", "data/runtime/odin_state_snapshot.json")
        )
        self.heartbeat_file = Path(os.getenv("ODIN_HEARTBEAT_FILE", "data/runtime/odin_heartbeat.json"))
        self.events_file = Path(os.getenv("ODIN_EVENTS_FILE", "data/runtime/odin_events.jsonl"))

        self.snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        self.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        self.events_file.parent.mkdir(parents=True, exist_ok=True)

        self.status = RuntimeStatus()
        self.health = OdinHealthcheck(log_root=log_root)
        self.assistant = AssistantRouter(controller)
        self.atlas = AtlasCoordinator(log_root=log_root)
        self.events = RuntimeEventLog(
            log_root=log_root,
            data_root=self.events_file.parent,
            events_file=self.events_file,
        )
        self.heartbeat = HeartbeatWriter(self.heartbeat_file)
        self.runtime_error_log = JsonlLogger(self.log_root / "errors" / "runtime_errors.log")

        self._last_healthcheck_ts = 0.0
        self._last_mt5_ts = 0.0
        self._last_atlas_ts = 0.0
        self._last_context_ts = 0.0
        self._running = False

    def _write_snapshot(self, payload: dict[str, Any]) -> None:
        safe_payload = redact_sensitive_data(payload)
        self.snapshot_file.write_text(
            json.dumps(safe_payload, sort_keys=True, default=str, indent=2) + "\n",
            encoding="utf-8",
        )

    def _runtime_blocked(self, reasons: list[str], *, state: RuntimeState = RuntimeState.BLOCKED) -> None:
        self.status.state = state
        self.status.safe_to_trade = False
        self.status.blocked_reasons = reasons
        self.status.reason = ",".join(reasons) if reasons else "blocked"

    def _current_snapshot(self, cycle: dict[str, Any], last_events: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "timestamp": now_iso(),
            "runtime_state": self.status.state.value,
            "odin_mode": os.getenv("ODIN_MODE", "SHADOW_MT5"),
            "safe_to_trade": self.status.safe_to_trade,
            "trading_real_enabled": os.getenv("ENABLE_REAL_TRADING", "false").lower() == "true",
            "mt5_order_send_enabled": os.getenv("MT5_ORDER_SEND_ENABLED", "false").lower() == "true",
            "xtb_real_enabled": os.getenv("XTB_REAL_ENABLED", "false").lower() == "true",
            "broker_real_enabled": os.getenv("BROKER_ALLOW_REAL_EXECUTION", "false").lower() == "true",
            "network": cycle.get("network", {}),
            "health": cycle.get("health", {}),
            "mt5": cycle.get("mt5", {}),
            "positions": cycle.get("positions", {}),
            "atlas": cycle.get("atlas", {}),
            "assistant": cycle.get("assistant", {}),
            "llm": cycle.get("llm", {}),
            "last_errors": cycle.get("last_errors", []),
            "last_events": last_events,
        }

    def _read_last_errors(self, limit: int = 5) -> list[str]:
        out: list[str] = []
        for path in [Path("logs/errors/errors.log"), Path("logs/system/errors.log")]:
            if not path.exists():
                continue
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            out.extend(lines[-limit:])
        return out[-limit:]

    def start(self) -> dict[str, Any]:
        if not self.runtime_enabled:
            self._runtime_blocked(["runtime_disabled"], state=RuntimeState.BLOCKED)
            return self.get_status()

        self.status.state = RuntimeState.STARTING
        self.status.started_at = now_iso()
        self.status.reason = "runtime_start_requested"
        self._running = True
        self.events.write("RUNTIME_STARTED", {"runtime_mode": self.runtime_mode})
        self.status.state = RuntimeState.RUNNING
        self.status.reason = "runtime_running"
        return self.get_status()

    def stop(self) -> dict[str, Any]:
        self.status.state = RuntimeState.STOPPING
        self.status.reason = "runtime_stop_requested"
        self.events.write("RUNTIME_STOPPED", {})
        self._running = False
        self.status.state = RuntimeState.STOPPED
        self.status.stopped_at = now_iso()
        return self.get_status()

    def pause(self) -> dict[str, Any]:
        self.status.state = RuntimeState.PAUSED
        self.status.reason = "runtime_paused"
        self.events.write("RUNTIME_PAUSED", {})
        return self.get_status()

    def resume(self) -> dict[str, Any]:
        self.status.state = RuntimeState.RUNNING
        self.status.reason = "runtime_resumed"
        self.events.write("RUNTIME_RESUMED", {})
        return self.get_status()

    def safe_shutdown(self) -> dict[str, Any]:
        self.status.state = RuntimeState.STOPPING
        self.status.reason = "safe_shutdown"
        self.events.write("RUNTIME_STOPPED", {"safe_shutdown": True})
        deadline = time.monotonic() + max(1, self.safe_shutdown_timeout_seconds)
        while time.monotonic() < deadline:
            time.sleep(0.01)
            break
        self._running = False
        self.status.state = RuntimeState.STOPPED
        self.status.stopped_at = now_iso()
        return self.get_status()

    def get_status(self) -> dict[str, Any]:
        return {
            **self.status.to_dict(),
            "runtime_enabled": self.runtime_enabled,
            "runtime_mode": self.runtime_mode,
            "heartbeat_seconds": self.heartbeat_seconds,
            "healthcheck_seconds": self.healthcheck_seconds,
            "mt5_poll_seconds": self.mt5_poll_seconds,
            "atlas_cycle_seconds": self.atlas_cycle_seconds,
            "assistant_context_seconds": self.assistant_context_seconds,
        }

    def snapshot(self) -> dict[str, Any]:
        if self.snapshot_file.exists():
            try:
                return json.loads(self.snapshot_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {"error": "invalid_snapshot_json"}
        return {"status": "missing_snapshot"}

    def run_once(self) -> dict[str, Any]:
        now_monotonic = time.monotonic()
        cycle: dict[str, Any] = {
            "network": {},
            "health": {},
            "mt5": {},
            "positions": {},
            "atlas": {},
            "assistant": {},
            "llm": {},
            "last_errors": self._read_last_errors(),
        }

        try:
            self.status.last_cycle_at = now_iso()
            self.status.cycle_count += 1

            heartbeat_payload = {
                "runtime_state": self.status.state.value,
                "cycle_count": self.status.cycle_count,
                "safe_to_trade": self.status.safe_to_trade,
            }
            hb = self.heartbeat.write(heartbeat_payload)
            self.status.last_heartbeat_at = hb["timestamp"]
            self.events.write("HEARTBEAT", hb)

            if now_monotonic - self._last_healthcheck_ts >= self.healthcheck_seconds:
                health = self.health.run()
                cycle["health"] = health
                self.status.last_healthcheck_at = now_iso()
                self._last_healthcheck_ts = now_monotonic
                hc_status = str(health.get("status", "WARNING"))
                if hc_status == "OK":
                    self.events.write("HEALTHCHECK_OK", {"status": hc_status})
                    if self.status.state not in {RuntimeState.PAUSED, RuntimeState.BLOCKED}:
                        self.status.state = RuntimeState.RUNNING
                        self.status.safe_to_trade = True
                        self.status.blocked_reasons = []
                elif hc_status == "WARNING":
                    self.events.write("HEALTHCHECK_WARNING", {"status": hc_status})
                    self.status.state = RuntimeState.DEGRADED
                    self.status.safe_to_trade = False
                elif hc_status == "BLOCKED":
                    self.events.write("HEALTHCHECK_BLOCKED", {"status": hc_status})
                    self._runtime_blocked(["healthcheck_blocked"])
                else:
                    self.events.write("HEALTHCHECK_CRITICAL", {"status": hc_status})
                    self._runtime_blocked(["healthcheck_critical"])
                    if self.stop_on_critical:
                        self.stop()

            if now_monotonic - self._last_mt5_ts >= self.mt5_poll_seconds:
                mt5_status = self.controller.execute("MT5_STATUS", actor="runtime", role="system")
                mt5_positions = self.controller.execute("MT5_LIST_POSITIONS", actor="runtime", role="system")
                mt5_sync = self.controller.execute("MT5_SYNC_POSITIONS", actor="runtime", role="system")
                cycle["mt5"] = mt5_status
                cycle["positions"] = {
                    "positions": mt5_positions,
                    "reconciliation": mt5_sync,
                }
                self._last_mt5_ts = now_monotonic
                self.events.write("MT5_STATUS_UPDATED", {"status": mt5_status.get("data", {}).get("mt5", {}).get("status")})
                self.events.write(
                    "MT5_RECONCILIATION_DONE",
                    {"recommended_state": mt5_sync.get("data", {}).get("recommended_state")},
                )

            if now_monotonic - self._last_context_ts >= self.assistant_context_seconds:
                q_state = self.assistant.ask("Qual é o estado do ODIN?", channel="runtime")
                cycle["assistant"] = q_state
                cycle["llm"] = self.assistant.llm_status()
                self._last_context_ts = now_monotonic
                self.events.write("ASSISTANT_CONTEXT_UPDATED", {"source": q_state.get("source")})

            if now_monotonic - self._last_atlas_ts >= self.atlas_cycle_seconds:
                atlas_result = self.atlas.run_shadow_cycle({"symbol": "EURUSD", "timeframe": "M15"})
                cycle["atlas"] = atlas_result
                self._last_atlas_ts = now_monotonic
                self.events.write(
                    "ATLAS_SHADOW_CYCLE_DONE",
                    {"status": atlas_result.get("status", "UNKNOWN")},
                )

            last_events = self.events.tail(20)
            snapshot = self._current_snapshot(cycle, last_events)
            self._write_snapshot(snapshot)
            self.status.reason = "cycle_ok"
            self.status.consecutive_errors = 0
            return {
                "accepted": True,
                "reason": "runtime_cycle_ok",
                "runtime": self.get_status(),
                "snapshot": snapshot,
            }
        except Exception as error:
            self.status.consecutive_errors += 1
            self.status.safe_to_trade = False
            self.status.reason = f"runtime_cycle_error:{error.__class__.__name__}"
            self.runtime_error_log.write(
                "runtime_error",
                {
                    "error": f"{error.__class__.__name__}: {error}",
                    "cycle_count": self.status.cycle_count,
                },
            )
            self.events.write(
                "ERROR",
                {
                    "error": f"{error.__class__.__name__}: {error}",
                    "cycle_count": self.status.cycle_count,
                },
            )
            if self.status.consecutive_errors >= self.max_cycle_errors:
                self.status.state = RuntimeState.DEGRADED
                self.status.reason = "runtime_max_cycle_errors"
                if self.auto_recovery:
                    self.status.state = RuntimeState.RECOVERY_MODE
                    self.events.write("RECOVERY_STARTED", {"reason": "max_cycle_errors"})
                    self.status.state = RuntimeState.DEGRADED
                    self.events.write("RECOVERY_COMPLETED", {"state": self.status.state.value})
            return {
                "accepted": False,
                "reason": self.status.reason,
                "runtime": self.get_status(),
            }

    def run_loop(self) -> dict[str, Any]:
        if not self._running:
            self.start()

        try:
            while self._running and self.status.state not in {RuntimeState.STOPPED, RuntimeState.KILLED}:
                if self.status.state == RuntimeState.PAUSED:
                    time.sleep(0.2)
                    continue
                self.run_once()
                time.sleep(max(0.2, self.heartbeat_seconds))
        except KeyboardInterrupt:
            self.events.write("RUNTIME_STOPPED", {"reason": "keyboard_interrupt"})
            return self.safe_shutdown()
        return self.get_status()
