from __future__ import annotations

from typing import Any

from shared.contracts import ActiveBlockVector, CorePublicStateView, GlobalStateSnapshot


class GlobalStatePublisher:
    def build_view(
        self,
        snapshot: GlobalStateSnapshot,
        block_vector: ActiveBlockVector,
        liveness_summary: dict[str, str],
        health_metrics: dict[str, Any] | None = None,
        learn_state_view=None,
    ) -> CorePublicStateView:
        return CorePublicStateView(
            state_code=snapshot.state_code,
            mode_code=snapshot.mode_code,
            status_summary=f"{snapshot.state_code.name.lower()}:{snapshot.readiness_class.value}",
            kill_active=snapshot.kill_active,
            dominant_block_reason=snapshot.dominant_block_reason,
            active_block_vector=block_vector,
            readiness_class=snapshot.readiness_class,
            integrity_class=snapshot.integrity_class,
            last_transition={
                "event": snapshot.last_transition_event,
                "at_utc": snapshot.last_transition_at_utc.isoformat(),
            },
            critical_module_liveness=liveness_summary,
            health_metrics=health_metrics or {},
            learn_state_view=learn_state_view,
        )
