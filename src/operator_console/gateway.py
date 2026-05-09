from __future__ import annotations

import json
from pathlib import Path
import tomllib
from typing import Any

from dash import CoreDashBridge, DashboardControlActionRequest, DashboardPermissionContext
from shared.config import OdinSettings, validate_settings
from shared.contracts import (
    ConfigStagingPatch,
    ConfigValidationReport,
    OperatorCommandRequest,
    OperatorCommandResult,
)
from shared.enums import GlobalState
from shared.enums import ExecutionProfile
from shared.utils import utc_now


CRITICAL_COMMANDS: tuple[str, ...] = ("stop", "pause", "resume")
READ_ONLY_COMMANDS: tuple[str, ...] = ("status", "get-config", "validate-config")
READ_ONLY_QUERY_NAMES: tuple[str, ...] = ("status", "health", "get-config", "external/status")


class CommandGateway:
    def __init__(
        self,
        runtime: Any,
        *,
        config_path: str | Path,
        bridge: CoreDashBridge | None = None,
        staging_enabled: bool = False,
        max_recent_logs: int = 50,
    ) -> None:
        self._runtime = runtime
        self._bridge = bridge or CoreDashBridge()
        self._config_path = Path(config_path)
        self._staging_enabled = staging_enabled
        self._max_recent_logs = max_recent_logs
        self._settings = runtime.get_settings()
        self._staged_patch: dict[str, Any] | None = None
        self._recent_logs: list[dict[str, Any]] = []
        self._audit_path = self._settings.runtime.log_dir / "operator-console-audit.jsonl"

    def execute(self, request: OperatorCommandRequest) -> OperatorCommandResult:
        command = request.command.strip().lower()
        if command in CRITICAL_COMMANDS and not request.confirmation:
            result = OperatorCommandResult(
                request_id=request.request_id,
                command=command,
                accepted=False,
                rejection_reason="confirmation_required",
                confirmation_required=True,
            )
            self._append_audit_entry(request, result)
            return result

        try:
            if command == "status":
                result = self._handle_status(request)
            elif command == "stop":
                result = self._dispatch_dash_control(request, "STOP")
            elif command == "pause":
                result = self._dispatch_dash_control(request, "PAUSE")
            elif command == "resume":
                result = self._dispatch_dash_control(request, "RESUME")
            elif command == "export-logs":
                result = self._dispatch_dash_control(request, "EXPORT_LOGS")
            elif command == "get-config":
                result = self._handle_get_config(request)
            elif command == "validate-config":
                result = self._handle_validate_config(request)
            else:
                result = OperatorCommandResult(
                    request_id=request.request_id,
                    command=command,
                    accepted=False,
                    rejection_reason="unsupported_command",
                )
        except Exception as error:
            result = OperatorCommandResult(
                request_id=request.request_id,
                command=command,
                accepted=False,
                rejection_reason=f"{error.__class__.__name__}:{error}",
            )
        self._append_audit_entry(request, result)
        return result

    def stage_config(self, staged_patch: ConfigStagingPatch) -> dict[str, Any]:
        if not self._staging_enabled:
            raise PermissionError("staging_disabled")
        self._staged_patch = dict(staged_patch.patch)
        return {
            "staging_enabled": self._staging_enabled,
            "stage_id": staged_patch.stage_id,
            "staged_by": staged_patch.staged_by,
            "staged_at_utc": staged_patch.staged_at_utc.isoformat(),
            "staged_patch": self._staged_patch,
        }

    def clear_staged_config(self) -> None:
        self._staged_patch = None

    def recent_logs(self) -> list[dict[str, Any]]:
        return list(self._recent_logs[-self._max_recent_logs :])

    def recent_audit_events(self, *, limit: int = 120) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        if not self._audit_path.exists():
            return []
        events: list[dict[str, Any]] = []
        try:
            for raw_line in self._audit_path.read_text(encoding="utf-8").splitlines():
                if not raw_line.strip():
                    continue
                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    events.append(payload)
        except OSError:
            return []
        return events[-limit:]

    def record_read_query(
        self,
        query_name: str,
        *,
        requested_by: str = "console-api",
        role: str = "operator",
    ) -> None:
        command = query_name.strip().lower()
        if command not in READ_ONLY_QUERY_NAMES:
            command = query_name.strip()
        entry = {
            "request_id": None,
            "command": command,
            "requested_by": requested_by,
            "role": role,
            "confirmation": False,
            "accepted": True,
            "rejection_reason": None,
            "read_only": True,
            "event_type": "read_query",
            "event_domain": "telemetry",
            "completed_at_utc": utc_now().isoformat(),
        }
        self._store_audit_entry(entry)

    def record_operational_event(
        self,
        *,
        command: str,
        accepted: bool,
        rejection_reason: str | None,
        requested_by: str = "console-api",
        role: str = "operator",
    ) -> None:
        entry = {
            "request_id": None,
            "command": command,
            "requested_by": requested_by,
            "role": role,
            "confirmation": False,
            "accepted": accepted,
            "rejection_reason": rejection_reason,
            "read_only": False,
            "event_type": "operational_event",
            "event_domain": "operator_command",
            "completed_at_utc": utc_now().isoformat(),
        }
        self._store_audit_entry(entry)

    def _permission_context(self, request: OperatorCommandRequest) -> DashboardPermissionContext:
        return DashboardPermissionContext.for_role(request.requested_by, request.role)

    def _dispatch_dash_control(
        self,
        request: OperatorCommandRequest,
        action_type: str,
    ) -> OperatorCommandResult:
        core_view = self._runtime.get_public_view()
        if (
            action_type in {"STOP", "PAUSE", "RESUME"}
            and core_view.state_code == GlobalState.OFFLINE
        ):
            return OperatorCommandResult(
                request_id=request.request_id,
                command=request.command,
                accepted=False,
                rejection_reason="runtime_not_active",
                response={
                    "requested_action": action_type,
                    "resulting_state": core_view.state_code.value,
                    "dispatched_event_type": None,
                    "view_payload": {},
                },
            )
        context = self._permission_context(request)
        auth = dict(request.authorization_context)
        auth.update(dict(request.payload))
        reason_text = request.payload.get("reason_text")
        result = self._bridge.dispatch(
            self._runtime,
            DashboardControlActionRequest(
                action_type=action_type,
                requested_by=request.requested_by,
                authorization_context=auth,
                reason_text=reason_text,
            ),
            context,
        )
        return OperatorCommandResult(
            request_id=request.request_id,
            command=request.command,
            accepted=result.accepted,
            rejection_reason=result.rejection_reason,
            confirmation_required=result.confirmation_required,
            response={
                "requested_action": result.requested_action,
                "resulting_state": (
                    result.resulting_state.value if result.resulting_state is not None else None
                ),
                "dispatched_event_type": result.dispatched_event_type,
                "view_payload": result.view_payload,
            },
        )

    def _handle_status(self, request: OperatorCommandRequest) -> OperatorCommandResult:
        context = self._permission_context(request)
        core_view = self._runtime.get_public_view()
        projection = self._bridge.project_state(
            core_view,
            context,
            runtime=self._runtime,
        )
        response = {
            "global_state": core_view.state_code.value,
            "mode": core_view.mode_code.value,
            "readiness_class": core_view.readiness_class.value,
            "integrity_class": core_view.integrity_class.value,
            "kill_active": core_view.kill_active,
            "active_block_count": core_view.active_block_vector.active_block_count,
            "critical_module_liveness": core_view.critical_module_liveness,
            "health_metrics": core_view.health_metrics,
            "dashboard_projection": projection.to_dict(),
            "market": self._runtime.get_market_runtime_status().to_dict(),
            "risk": {"status": "not_integrated_in_console_cut_1"},
            "decision": {"status": "not_integrated_in_console_cut_1"},
            "exec": {"status": "not_integrated_in_console_cut_1"},
            "recovery": {"status": "not_integrated_in_console_cut_1"},
            "recent_logs": self.recent_logs(),
        }
        return OperatorCommandResult(
            request_id=request.request_id,
            command=request.command,
            accepted=True,
            response=response,
        )

    def _handle_get_config(self, request: OperatorCommandRequest) -> OperatorCommandResult:
        active_raw = self._load_raw_config()
        merged_raw = self._merge_raw_with_staged(active_raw)
        return OperatorCommandResult(
            request_id=request.request_id,
            command=request.command,
            accepted=True,
            response={
                "config_path": str(self._config_path),
                "staging_enabled": self._staging_enabled,
                "active_config": active_raw,
                "staged_patch": self._staged_patch,
                "staged_preview": merged_raw,
            },
        )

    def _handle_validate_config(self, request: OperatorCommandRequest) -> OperatorCommandResult:
        expected_profile_value = request.payload.get("expect_profile")
        expected_profile = (
            ExecutionProfile(str(expected_profile_value)) if expected_profile_value else None
        )
        use_staged = bool(request.payload.get("use_staged", True))
        active_raw = self._load_raw_config()
        validation_raw = self._merge_raw_with_staged(active_raw) if use_staged else active_raw
        try:
            settings = OdinSettings.from_raw(validation_raw)
            errors = tuple(validate_settings(settings, expected_profile=expected_profile))
            report = ConfigValidationReport(
                is_valid=not errors,
                profile=settings.profile.name.value,
                dashboard_surface=settings.dashboard.surface.value,
                errors=errors,
            )
            response = report.to_dict()
        except Exception as error:
            report = ConfigValidationReport(
                is_valid=False,
                profile="unknown",
                dashboard_surface="unknown",
                errors=(f"{error.__class__.__name__}: {error}",),
            )
            response = report.to_dict()

        response["validation_source"] = "staged_preview" if use_staged else "active_config"
        return OperatorCommandResult(
            request_id=request.request_id,
            command=request.command,
            accepted=True,
            response=response,
        )

    def _append_audit_entry(
        self,
        request: OperatorCommandRequest,
        result: OperatorCommandResult,
    ) -> None:
        command = request.command.strip().lower()
        read_only = command in READ_ONLY_COMMANDS
        entry = {
            "request_id": request.request_id,
            "command": request.command,
            "requested_by": request.requested_by,
            "role": request.role,
            "confirmation": request.confirmation,
            "accepted": result.accepted,
            "rejection_reason": result.rejection_reason,
            "read_only": read_only,
            "event_type": "read_query" if read_only else "operational_event",
            "event_domain": "telemetry" if read_only else "operator_command",
            "completed_at_utc": result.completed_at_utc.isoformat(),
        }
        self._store_audit_entry(entry)

    def _store_audit_entry(self, entry: dict[str, Any]) -> None:
        if str(entry.get("event_type")) == "operational_event":
            self._recent_logs.append(entry)
            self._recent_logs = self._recent_logs[-self._max_recent_logs :]
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self._audit_path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(entry, sort_keys=True) + "\n")

    def _load_raw_config(self) -> dict[str, Any]:
        return tomllib.loads(self._config_path.read_text(encoding="utf-8"))

    def _merge_raw_with_staged(self, raw: dict[str, Any]) -> dict[str, Any]:
        if not self._staged_patch:
            return raw
        merged = json.loads(json.dumps(raw))
        self._merge_dicts(merged, self._staged_patch)
        return merged

    def _merge_dicts(self, target: dict[str, Any], patch: dict[str, Any]) -> None:
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                self._merge_dicts(target[key], value)
            else:
                target[key] = value
