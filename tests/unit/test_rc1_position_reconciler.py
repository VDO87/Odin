from odin_execution.position_reconciler import PositionReconciler
from odin_execution.position_registry import Position, PositionRegistry


def test_position_reconciler_classifies_missing_and_unprotected() -> None:
    registry = PositionRegistry(odin_magic=870087)
    registry.set_expected([Position(position_id="101", symbol="EURUSD", volume=0.1, magic=870087)])

    reconciler = PositionReconciler(registry, odin_magic=870087)
    mt5_positions = [
        {"ticket": "102", "symbol": "EURUSD", "magic": 870087, "sl": 0, "tp": 0},
    ]
    result = reconciler.reconcile(mt5_positions)

    assert result["ok"] is False
    assert len(result["classes"]["MISSING_POSITION"]) == 1
    assert len(result["classes"]["UNPROTECTED_POSITION"]) == 1
