from __future__ import annotations

from shared.contracts import CorePublicStateView, RecoverySnapshot
from shared.enums import BlockCode, GlobalState

from dash.models import DashboardActionAvailability


class ActionAvailabilityResolver:
    def resolve(
        self,
        core_view: CorePublicStateView,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
    ) -> DashboardActionAvailability:
        available: list[str] = []
        confirmation_required = {
            "STOP",
            "MODE_CHANGE",
            "MAINTENANCE_ENTER",
            "REQUEST_RECOVERY_VALIDATION",
            "MANUAL_BLOCK",
            "MANUAL_CLEAR",
        }

        if core_view.state_code == GlobalState.OFFLINE:
            available.append("START")
        else:
            available.append("STOP")

        if core_view.state_code in {GlobalState.MONITORING, GlobalState.READY, GlobalState.ACTIVE}:
            available.append("PAUSE")
        if core_view.state_code in {GlobalState.PAUSED, GlobalState.BLOCKED_RISK}:
            available.append("RESUME")
        if core_view.state_code in {
            GlobalState.IDLE,
            GlobalState.MONITORING,
            GlobalState.READY,
            GlobalState.PAUSED,
        }:
            available.append("MODE_CHANGE")
        if core_view.state_code != GlobalState.OFFLINE and not core_view.active_block_vector.has_code(BlockCode.MANUAL):
            available.append("MANUAL_BLOCK")
        if core_view.active_block_vector.has_code(BlockCode.MANUAL):
            available.append("MANUAL_CLEAR")
        if core_view.state_code != GlobalState.OFFLINE:
            available.append("MAINTENANCE_ENTER")
        if core_view.state_code == GlobalState.MAINTENANCE:
            available.append("MAINTENANCE_EXIT")
        if core_view.state_code in {GlobalState.RECOVERY, GlobalState.BLOCKED_FAULT, GlobalState.ERROR}:
            available.append("REQUEST_RECOVERY_VALIDATION")
        available.append("EXPORT_LOGS")

        has_manual_block = core_view.active_block_vector.has_code(BlockCode.MANUAL)
        has_risk_block = core_view.active_block_vector.has_code(BlockCode.RISK)
        if core_view.kill_active or has_manual_block or has_risk_block:
            available = [action for action in available if action != "RESUME"]
        if recovery_snapshot is not None and recovery_snapshot.result.manual_intervention_required:
            available = [action for action in available if action != "RESUME"]

        available_tuple = tuple(dict.fromkeys(available))
        all_actions = {
            "START",
            "STOP",
            "PAUSE",
            "RESUME",
            "MODE_CHANGE",
            "MANUAL_BLOCK",
            "MANUAL_CLEAR",
            "MAINTENANCE_ENTER",
            "MAINTENANCE_EXIT",
            "REQUEST_RECOVERY_VALIDATION",
            "EXPORT_LOGS",
        }
        forbidden = tuple(sorted(all_actions.difference(available_tuple)))
        required_confirmations = tuple(
            action for action in available_tuple if action in confirmation_required
        )
        return DashboardActionAvailability(
            available_actions=available_tuple,
            forbidden_actions=forbidden,
            confirmation_required_actions=required_confirmations,
            maintenance_profile_required="MAINTENANCE_ENTER" in available_tuple,
            resume_allowed="RESUME" in available_tuple,
        )
