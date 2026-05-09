from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.runtime import CoreRuntimeController
from shared.contracts import CoreEventEnvelope, CorePublicStateView


@dataclass(frozen=True, slots=True)
class ReplayStep:
    event_id: str
    event_type: str
    state_code: str
    dominant_block_reason: str | None
    active_block_count: int


@dataclass(frozen=True, slots=True)
class ReplayResult:
    initial_state: str
    final_state: str
    final_mode: str
    final_dominant_block_reason: str | None
    final_block_codes: tuple[str, ...]
    timeline: tuple[ReplayStep, ...]

    def fingerprint(self) -> tuple[object, ...]:
        return (
            self.initial_state,
            self.final_state,
            self.final_mode,
            self.final_dominant_block_reason,
            self.final_block_codes,
            tuple((step.event_type, step.state_code, step.dominant_block_reason, step.active_block_count) for step in self.timeline),
        )


class EventReplayEngine:
    def replay(
        self,
        runtime: CoreRuntimeController,
        events: Iterable[CoreEventEnvelope],
    ) -> ReplayResult:
        initial_view = runtime.start()
        timeline: list[ReplayStep] = []

        for event in events:
            view = runtime.process_event(event)
            timeline.append(self._step_from_view(event, view))

        final_view = runtime.get_public_view()
        return ReplayResult(
            initial_state=initial_view.state_code.value,
            final_state=final_view.state_code.value,
            final_mode=final_view.mode_code.value,
            final_dominant_block_reason=final_view.dominant_block_reason,
            final_block_codes=tuple(block.block_code.value for block in final_view.active_block_vector.blocks),
            timeline=tuple(timeline),
        )

    def _step_from_view(self, event: CoreEventEnvelope, view: CorePublicStateView) -> ReplayStep:
        return ReplayStep(
            event_id=event.event_id,
            event_type=event.event_type,
            state_code=view.state_code.value,
            dominant_block_reason=view.dominant_block_reason,
            active_block_count=view.active_block_vector.active_block_count,
        )
