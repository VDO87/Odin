from __future__ import annotations

from shared.contracts import CorePublicStateView, ExecutionStateUpdate, RecoverySnapshot
from shared.enums import EventType, PromotionResult

from dash.models import DashboardAlarmItem


class AlarmCenter:
    def build(
        self,
        core_view: CorePublicStateView,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
        latest_exec_update: ExecutionStateUpdate | None = None,
    ) -> tuple[DashboardAlarmItem, ...]:
        alarms: list[DashboardAlarmItem] = []

        if core_view.kill_active:
            alarms.append(
                DashboardAlarmItem(
                    severity="CRITICAL",
                    alarm_type="kill_active",
                    source_module="CORE",
                    title="Kill ativo",
                    summary="Kill persistente ou ativo impede operação.",
                    linked_state_ref=core_view.state_code.value,
                )
            )

        if core_view.health_metrics.get("persistence_status") == "failed":
            alarms.append(
                DashboardAlarmItem(
                    severity="CRITICAL",
                    alarm_type="persistence_failed",
                    source_module="CORE",
                    title="Persistência crítica falhou",
                    summary=str(
                        core_view.health_metrics.get("last_persistence_error")
                        or "Falha de persistência crítica sem detalhe adicional."
                    ),
                    linked_state_ref=core_view.state_code.value,
                )
            )

        for block in core_view.active_block_vector.blocks:
            severity = block.severity.name
            alarms.append(
                DashboardAlarmItem(
                    severity=severity,
                    alarm_type=block.block_code.value,
                    source_module=block.source_module,
                    title=f"Bloqueio {block.block_code.value}",
                    summary=block.reason_code,
                    linked_state_ref=block.block_id,
                )
            )

        for module_name, status in core_view.critical_module_liveness.items():
            if status == "TIMEOUT":
                alarms.append(
                    DashboardAlarmItem(
                        severity="CRITICAL",
                        alarm_type="heartbeat_timeout",
                        source_module=module_name,
                        title=f"Timeout de heartbeat em {module_name}",
                        summary="Modulo crítico sem heartbeat dentro da janela suportada.",
                        linked_state_ref=module_name,
                    )
                )

        if latest_exec_update is not None:
            if latest_exec_update.event_type == EventType.EXEC_DIVERGENCE.value:
                alarms.append(
                    DashboardAlarmItem(
                        severity="CRITICAL",
                        alarm_type="exec_divergence",
                        source_module="EXEC",
                        title="Divergência executória",
                        summary=latest_exec_update.reason_summary or "Divergência crítica reportada pelo EXEC.",
                        linked_state_ref=latest_exec_update.intent_id,
                    )
                )
            elif latest_exec_update.event_type == EventType.EXEC_REJECTED_SLIPPAGE.value:
                alarms.append(
                    DashboardAlarmItem(
                        severity="WARN",
                        alarm_type="slippage_rejected",
                        source_module="EXEC",
                        title="Slippage rejeitado",
                        summary=latest_exec_update.reason_summary or "Execução rejeitada por slippage.",
                        linked_state_ref=latest_exec_update.intent_id,
                    )
                )
            elif latest_exec_update.event_type == EventType.INTENTION_EXPIRED.value:
                alarms.append(
                    DashboardAlarmItem(
                        severity="WARN",
                        alarm_type="intention_expired",
                        source_module="EXEC",
                        title="Intenção expirada",
                        summary=latest_exec_update.reason_summary or "Intenção expirada antes da execução.",
                        linked_state_ref=latest_exec_update.intent_id,
                    )
                )

        if recovery_snapshot is not None:
            if recovery_snapshot.result.result_code.value in {"RCV-30", "RCV-40", "RCV-50"}:
                alarms.append(
                    DashboardAlarmItem(
                        severity="CRITICAL"
                        if recovery_snapshot.result.result_code.value in {"RCV-40", "RCV-50"}
                        else "WARN",
                        alarm_type="recovery_attention",
                        source_module="RECOVERY",
                        title="Recovery requer atenção",
                        summary=recovery_snapshot.result.result_summary,
                        linked_state_ref=recovery_snapshot.result.recovery_id,
                    )
                )

        learn_state_view = core_view.learn_state_view
        if learn_state_view is not None and learn_state_view.rollback_state is not None:
            alarms.append(
                DashboardAlarmItem(
                    severity="WARN",
                    alarm_type="learn_rollback",
                    source_module="LEARN",
                    title="Rollback do LEARN registado",
                    summary=learn_state_view.rollback_state.value,
                    linked_state_ref=learn_state_view.active_version,
                )
            )
        if learn_state_view is not None and learn_state_view.shadow_required:
            if learn_state_view.shadow_session_id is None:
                alarms.append(
                    DashboardAlarmItem(
                        severity="WARN",
                        alarm_type="learn_shadow_pending",
                        source_module="LEARN",
                        title="Shadow mode pendente",
                        summary="Proposta requer shadow mode antes de ativação.",
                        linked_state_ref=learn_state_view.pending_proposal_id,
                    )
                )
            elif learn_state_view.shadow_ended_at_utc is None:
                alarms.append(
                    DashboardAlarmItem(
                        severity="INFO",
                        alarm_type="learn_shadow_running",
                        source_module="LEARN",
                        title="Shadow mode em execução",
                        summary=learn_state_view.shadow_scope or "Sessão de shadow ativa.",
                        linked_state_ref=learn_state_view.shadow_session_id,
                    )
                )
        if (
            learn_state_view is not None
            and learn_state_view.shadow_promotion_recommendation
            in {PromotionResult.REJECT, PromotionResult.ROLLBACK_REQUIRED}
        ):
            alarms.append(
                DashboardAlarmItem(
                    severity="WARN",
                    alarm_type="learn_shadow_recommendation",
                    source_module="LEARN",
                    title="Shadow recomenda não promover",
                    summary=learn_state_view.shadow_promotion_recommendation.value,
                    linked_state_ref=learn_state_view.shadow_session_id,
                )
            )

        severity_order = {"CRITICAL": 0, "ERROR": 1, "WARN": 2, "INFO": 3}
        return tuple(sorted(alarms, key=lambda item: (severity_order.get(item.severity, 9), item.created_at_utc)))
