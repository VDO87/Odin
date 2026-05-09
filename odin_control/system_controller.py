from __future__ import annotations

from pathlib import Path
from typing import Any

from odin_control.command_bus import CommandBus, CommandRequest
from odin_control.network_monitor import NetworkMonitor
from odin_control.permissions import PermissionManager
from odin_control.recovery_manager import RecoveryManager
from odin_control.state_machine import OdinState, OdinStateMachine
from odin_logs.audit import AuditLogger
from odin_logs.logger import JsonlLogger


class SystemController:
    def __init__(self, log_root: str | Path = "logs") -> None:
        log_root_path = Path(log_root)
        self.machine = OdinStateMachine()
        self.network = NetworkMonitor()
        self.recovery = RecoveryManager(self.machine)
        self.audit = AuditLogger(log_root_path / "control" / "commands.log")
        self.transitions = JsonlLogger(log_root_path / "control" / "state_transitions.log")
        self.risk_engine_mandatory = True
        self.real_trading_enabled = False

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
                "RELOAD_CONFIG": self._reload_config,
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
        if self.machine.state in {OdinState.KILLED, OdinState.STOPPED}:
            return {"accepted": False, "reason": "runtime_not_active"}
        if not self._to(OdinState.HEALTHCHECK, "manual_healthcheck"):
            return {"accepted": False, "reason": "invalid_state_for_healthcheck"}
        self._to(OdinState.READY, "healthcheck_completed")
        return {"accepted": True, "reason": "healthcheck_ok"}

    def _sync_mt5(self, _: CommandRequest) -> dict[str, Any]:
        if not self._to(OdinState.POSITION_RECONCILIATION, "manual_mt5_sync"):
            return {"accepted": False, "reason": "invalid_state_for_sync"}
        self._to(OdinState.READY, "mt5_sync_completed")
        return {"accepted": True, "reason": "mt5_synced"}

    def _reload_config(self, _: CommandRequest) -> dict[str, Any]:
        return {"accepted": True, "reason": "config_reloaded"}

    def execute(self, command: str, actor: str = "operator", role: str = "operator") -> dict[str, Any]:
        result = self.command_bus.execute(CommandRequest(command=command, actor=actor, role=role))
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
