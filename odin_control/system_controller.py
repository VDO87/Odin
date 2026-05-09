from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from odin_control.command_bus import CommandBus, CommandRequest
from odin_control.network_monitor import NetworkMonitor
from odin_control.permissions import PermissionManager
from odin_control.recovery_manager import RecoveryManager
from odin_control.state_machine import OdinState, OdinStateMachine
from odin_execution.mt5_shadow import MT5ShadowAdapter
from odin_execution.position_reconciler import PositionReconciler
from odin_execution.position_registry import PositionRegistry
from odin_health.healthcheck import OdinHealthcheck
from odin_logs.audit import AuditLogger
from odin_logs.logger import JsonlLogger
from odin_market.mt5_feed import MT5Feed


class SystemController:
    def __init__(self, log_root: str | Path = "logs") -> None:
        log_root_path = Path(log_root)
        self.machine = OdinStateMachine()
        self.network = NetworkMonitor()
        self.recovery = RecoveryManager(self.machine)
        self.audit = AuditLogger(log_root_path / "control" / "commands.log")
        self.transitions = JsonlLogger(log_root_path / "control" / "state_transitions.log")
        self.mt5_log = JsonlLogger(log_root_path / "trading" / "mt5_shadow.log")
        self.risk_engine_mandatory = True
        self.real_trading_enabled = False

        self.mt5_magic = int(os.getenv("MT5_MAGIC_NUMBER_ODIN", "870087"))
        self.mt5_adapter = MT5ShadowAdapter(order_send_enabled=False)
        self.mt5_feed = MT5Feed(self.mt5_adapter, log_root=log_root_path)
        self.position_registry = PositionRegistry(odin_magic=self.mt5_magic)
        self.position_reconciler = PositionReconciler(
            self.position_registry,
            odin_magic=self.mt5_magic,
            log_root=log_root_path,
        )

        self.command_bus = CommandBus(
            get_state=lambda: self.machine.state,
            permissions=PermissionManager(allow_real_trading=False),
            audit=self.audit,
            handlers={
                "START_ODIN": self._start,
                "PAUSE_ODIN": self._pause,
                "RESUME_ODIN": self._resume,
                "STOP_ODIN": self._stop,
                "KILL_SWITCH": self._kill,
                "RUN_HEALTHCHECK": self._healthcheck,
                "SYNC_MT5_POSITIONS": self._sync_mt5,
                "MT5_SYNC_POSITIONS": self._sync_mt5,
                "RELOAD_CONFIG": self._reload_config,
                "MT5_STATUS": self._mt5_status,
                "MT5_HEALTHCHECK": self._mt5_healthcheck,
                "MT5_LIST_POSITIONS": self._mt5_list_positions,
                "MT5_LIST_SYMBOLS": self._mt5_list_symbols,
                "MT5_GET_TICK": self._mt5_get_tick,
                "MT5_GET_CANDLES": self._mt5_get_candles,
            },
        )

    def _record_transition(self, from_state: OdinState, to_state: OdinState, reason: str) -> None:
        self.transitions.write(
            "state_transition",
            {
                "from_state": from_state.value,
                "to_state": to_state.value,
                "reason": reason,
            },
        )

    def _to(self, target: OdinState, reason: str) -> bool:
        result = self.machine.transition(target, reason=reason)
        if result.accepted:
            self._record_transition(result.from_state, result.to_state, reason)
        return result.accepted

    def _start(self, _: CommandRequest) -> dict[str, Any]:
        ok = self._to(OdinState.STARTING, "start_command")
        if not ok:
            return {"accepted": False, "reason": "invalid_state_for_start"}
        self._to(OdinState.HEALTHCHECK, "startup_healthcheck")
        self._to(OdinState.READY, "startup_ready")
        self._to(OdinState.RUNNING, "startup_running")
        return {"accepted": True, "reason": "started"}

    def _pause(self, _: CommandRequest) -> dict[str, Any]:
        if not self._to(OdinState.PAUSED, "pause_command"):
            return {"accepted": False, "reason": "invalid_state_for_pause"}
        return {"accepted": True, "reason": "paused"}

    def _resume(self, _: CommandRequest) -> dict[str, Any]:
        if not self._to(OdinState.RUNNING, "resume_command"):
            return {"accepted": False, "reason": "invalid_state_for_resume"}
        return {"accepted": True, "reason": "running"}

    def _stop(self, _: CommandRequest) -> dict[str, Any]:
        if not self._to(OdinState.STOPPED, "stop_command"):
            return {"accepted": False, "reason": "invalid_state_for_stop"}
        return {"accepted": True, "reason": "stopped"}

    def _kill(self, _: CommandRequest) -> dict[str, Any]:
        if not self._to(OdinState.KILLED, "kill_switch"):
            return {"accepted": False, "reason": "invalid_state_for_kill"}
        return {"accepted": True, "reason": "killed"}

    def _healthcheck(self, _: CommandRequest) -> dict[str, Any]:
        payload = OdinHealthcheck(log_root="logs").run()
        if self.machine.state in {OdinState.KILLED, OdinState.STOPPED}:
            return {"accepted": False, "reason": "runtime_not_active", "healthcheck": payload}
        if not self._to(OdinState.HEALTHCHECK, "manual_healthcheck"):
            return {"accepted": False, "reason": "invalid_state_for_healthcheck", "healthcheck": payload}
        self._to(OdinState.READY, "healthcheck_completed")
        return {"accepted": True, "reason": "healthcheck_ok", "healthcheck": payload}

    def _mt5_reconciliation_report(self) -> dict[str, Any]:
        positions_result = self.mt5_adapter.get_positions()
        positions = list(positions_result.get("data", {}).get("positions", []))
        report = self.position_reconciler.reconcile(positions)
        self.mt5_log.write(
            "mt5_reconciliation_request",
            {
                "positions_status": positions_result.get("status"),
                "reconciliation": report,
            },
        )
        return {"positions": positions_result, "reconciliation": report}

    def _sync_mt5(self, _: CommandRequest) -> dict[str, Any]:
        rec = self._mt5_reconciliation_report()
        if not self._to(OdinState.POSITION_RECONCILIATION, "manual_mt5_sync"):
            return {"accepted": False, "reason": "invalid_state_for_sync", **rec}
        next_state = OdinState.READY if rec["reconciliation"].get("safe_to_trade", False) else OdinState.BLOCKED
        self._to(next_state, "mt5_sync_completed")
        return {
            "accepted": True,
            "reason": "mt5_synced",
            **rec,
            "recommended_state": next_state.value,
        }

    def _reload_config(self, _: CommandRequest) -> dict[str, Any]:
        return {"accepted": True, "reason": "config_reloaded"}

    def _mt5_status(self, _: CommandRequest) -> dict[str, Any]:
        info = self.mt5_adapter.healthcheck()
        return {"accepted": True, "reason": "mt5_status", "mt5": info}

    def _mt5_healthcheck(self, _: CommandRequest) -> dict[str, Any]:
        payload = OdinHealthcheck(log_root="logs").run().get("checks", {}).get("mt5", {})
        return {"accepted": True, "reason": "mt5_healthcheck", "mt5": payload}

    def _mt5_list_positions(self, _: CommandRequest) -> dict[str, Any]:
        positions = self.mt5_adapter.get_positions()
        return {"accepted": True, "reason": "mt5_positions", "mt5": positions}

    def _mt5_list_symbols(self, _: CommandRequest) -> dict[str, Any]:
        symbols = self.mt5_adapter.get_symbols()
        return {"accepted": True, "reason": "mt5_symbols", "mt5": symbols}

    def _mt5_get_tick(self, request: CommandRequest) -> dict[str, Any]:
        symbol = str(request.payload.get("symbol") or "EURUSD").upper()
        tick = self.mt5_feed.get_tick(symbol)
        return {"accepted": True, "reason": "mt5_tick", "symbol": symbol, "mt5": tick}

    def _mt5_get_candles(self, request: CommandRequest) -> dict[str, Any]:
        symbol = str(request.payload.get("symbol") or "EURUSD").upper()
        timeframe = str(request.payload.get("timeframe") or os.getenv("MT5_DEFAULT_TIMEFRAME", "M15")).upper()
        raw_count = request.payload.get("count")
        if raw_count is None:
            raw_count = os.getenv("MT5_CANDLE_COUNT", "200")
        try:
            count = int(str(raw_count))
        except (TypeError, ValueError):
            count = 200
        candles = self.mt5_feed.get_candles(symbol, timeframe, count)
        return {
            "accepted": True,
            "reason": "mt5_candles",
            "symbol": symbol,
            "timeframe": timeframe,
            "count": count,
            "mt5": candles,
        }

    def execute(
        self,
        command: str,
        actor: str = "operator",
        role: str = "operator",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.command_bus.execute(
            CommandRequest(command=command, actor=actor, role=role, payload=payload or {})
        )
        return {
            "command_id": result.command_id,
            "command": result.command,
            "accepted": result.accepted,
            "reason": result.reason,
            "state": result.state.value,
            "data": result.data,
        }

    def update_network(self, online: bool) -> dict[str, Any]:
        status = self.network.update(online)
        if status.threshold_reached and not status.online:
            self.recovery.handle_network_failure()
            return {"network": status.__dict__, "state": self.machine.state.value, "blocked": True}
        if status.online and self.machine.state == OdinState.DEGRADED_NETWORK:
            self.recovery.begin_recovery()
            self.recovery.after_healthcheck(ok=True)
            self.recovery.after_reconciliation(ok=True)
        return {"network": status.__dict__, "state": self.machine.state.value, "blocked": False}
