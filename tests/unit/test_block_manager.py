from core.blocks import BlockManager
from shared.contracts import BlockEntry
from shared.enums import BlockCode, Severity


def test_block_manager_keeps_highest_priority_block_as_dominant() -> None:
    manager = BlockManager()
    manager.apply_block(
        BlockEntry(
            block_code=BlockCode.RISK,
            source_module="RISK",
            severity=Severity.ERROR,
            reason_code="risk_block",
            manual_clear_required=False,
            clearable_by_recovery=True,
        )
    )
    manager.apply_block(
        BlockEntry(
            block_code=BlockCode.KILL,
            source_module="RISK",
            severity=Severity.CRITICAL,
            reason_code="kill_active",
            manual_clear_required=True,
            clearable_by_recovery=False,
        )
    )

    vector = manager.as_vector()

    assert vector.active_block_count == 2
    assert vector.dominant_block_reason == "kill_active"
    assert vector.manual_clear_required is True


def test_manual_block_is_not_cleared_without_explicit_permission() -> None:
    manager = BlockManager()
    block = BlockEntry(
        block_code=BlockCode.MANUAL,
        source_module="DASH",
        severity=Severity.ERROR,
        reason_code="manual_pause",
        manual_clear_required=True,
        clearable_by_recovery=False,
    )
    manager.apply_block(block)

    assert manager.clear_block(block.block_id) is False
    assert manager.clear_block(block.block_id, allow_manual=True) is True


def test_manual_block_is_not_cleared_by_recovery_flow() -> None:
    manager = BlockManager()
    manager.apply_block(
        BlockEntry(
            block_code=BlockCode.MANUAL,
            source_module="DASH",
            severity=Severity.ERROR,
            reason_code="manual_hold",
            manual_clear_required=True,
            clearable_by_recovery=False,
        )
    )

    assert manager.clear_by_code(BlockCode.MANUAL, via_recovery=True) == 0
    assert manager.as_vector().has_code(BlockCode.MANUAL) is True


def test_manual_block_has_precedence_over_fault_in_dominant_reason() -> None:
    manager = BlockManager()
    manager.apply_block(
        BlockEntry(
            block_code=BlockCode.FAULT,
            source_module="CORE",
            severity=Severity.CRITICAL,
            reason_code="fault_block",
            manual_clear_required=False,
            clearable_by_recovery=True,
        )
    )
    manager.apply_block(
        BlockEntry(
            block_code=BlockCode.MANUAL,
            source_module="DASH",
            severity=Severity.ERROR,
            reason_code="manual_hold",
            manual_clear_required=True,
            clearable_by_recovery=False,
        )
    )

    vector = manager.as_vector()

    assert vector.active_block_count == 2
    assert vector.dominant_block_reason == "manual_hold"
