from odin_execution.position_reconciler import PositionReconciler
from odin_execution.position_registry import Position, PositionRegistry


def test_mt5_reconciler_classifies_all_required_categories() -> None:
    registry = PositionRegistry(odin_magic=870087)
    registry.set_expected([Position(position_id="1", symbol="EURUSD", volume=0.1, magic=870087)])
    reconciler = PositionReconciler(registry, odin_magic=870087)

    mt5_positions = [
        {"ticket": "1", "symbol": "EURUSD", "magic": 870087, "sl": 1.0, "tp": 2.0},
        {"ticket": "2", "symbol": "EURUSD", "magic": 111111, "sl": 1.0, "tp": 2.0},
        {"ticket": "3", "symbol": "EURUSD", "magic": 870087, "sl": 0, "tp": 0},
        {"ticket": "4", "symbol": "EURUSD", "sl": 1.0, "tp": 2.0},
        {"ticket": "5", "symbol": "EURUSD", "magic": 870087, "sl": 1.0, "tp": 2.0},
    ]

    report = reconciler.reconcile(mt5_positions)
    assert report["total_positions"] == 5
    assert report["odin_managed"] == 1
    assert report["external_positions"] == 1
    assert report["orphan_positions"] == 1
    assert report["unprotected_positions"] == 1
    assert report["unknown_magic"] == 1
    assert report["recommended_state"] == "BLOCKED"
    assert report["safe_to_trade"] is False
