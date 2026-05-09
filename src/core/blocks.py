from __future__ import annotations

from shared.contracts import ActiveBlockVector, BlockEntry
from shared.enums import BlockCode


BLOCK_PRIORITIES: dict[BlockCode, int] = {
    BlockCode.KILL: 100,
    BlockCode.MANUAL: 90,
    BlockCode.FAULT: 80,
    BlockCode.RECOVERY_PENDING: 70,
    BlockCode.RISK: 60,
    BlockCode.ADMIN: 50,
    BlockCode.MAINTENANCE: 40,
}


class BlockManager:
    def __init__(self, initial_vector: ActiveBlockVector | None = None) -> None:
        self._blocks: dict[str, BlockEntry] = {}
        if initial_vector is not None:
            self._blocks = {block.block_id: block for block in initial_vector.blocks}

    def apply_block(self, block: BlockEntry) -> None:
        self._blocks[block.block_id] = block

    def clear_block(
        self,
        block_id: str,
        *,
        allow_manual: bool = False,
        via_recovery: bool = False,
    ) -> bool:
        block = self._blocks.get(block_id)
        if block is None:
            return False
        if block.manual_clear_required and not allow_manual:
            return False
        if via_recovery and not block.clearable_by_recovery:
            return False
        self._blocks.pop(block_id, None)
        return True

    def clear_by_code(
        self,
        code: BlockCode,
        *,
        allow_manual: bool = False,
        via_recovery: bool = False,
    ) -> int:
        cleared = 0
        for block in list(self._blocks.values()):
            if block.block_code != code:
                continue
            if self.clear_block(
                block.block_id,
                allow_manual=allow_manual,
                via_recovery=via_recovery,
            ):
                cleared += 1
        return cleared

    def as_vector(self) -> ActiveBlockVector:
        blocks = tuple(sorted(self._blocks.values(), key=self._priority_sort_key))
        dominant = blocks[0] if blocks else None
        return ActiveBlockVector(
            blocks=blocks,
            dominant_block_reason=dominant.reason_code if dominant else None,
            dominant_block_priority=BLOCK_PRIORITIES.get(dominant.block_code, 0)
            if dominant
            else 0,
            manual_clear_required=any(block.manual_clear_required for block in blocks),
        )

    def _priority_sort_key(self, block: BlockEntry) -> tuple[int, float]:
        return (-BLOCK_PRIORITIES.get(block.block_code, 0), block.created_at_utc.timestamp())
