from __future__ import annotations

from odin_atlas.coordinator import AtlasCoordinator


def test_atlas_keeps_shadow_only_when_llm_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_ENABLED", "true")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")

    coordinator = AtlasCoordinator(log_root="logs")
    result = coordinator.analyze({"symbol": "EURUSD", "timeframe": "M15"})

    assert result["atlas_executes_orders"] is False
    assert result["decision_packet"]["execution_permission"] == "SHADOW_ONLY"
    assert "critic_explanation" in result
    assert "memory_note" in result
