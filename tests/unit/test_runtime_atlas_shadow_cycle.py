from __future__ import annotations

from odin_atlas.coordinator import AtlasCoordinator


def test_atlas_shadow_cycle_uses_shadow_only() -> None:
    coordinator = AtlasCoordinator(log_root="logs")
    result = coordinator.run_shadow_cycle({"symbol": "EURUSD", "timeframe": "M15"})
    assert result["execution_permission"] == "SHADOW_ONLY"
    assert result["atlas_executes_orders"] is False
