from __future__ import annotations

from odin_dashboard.state_provider import DashboardStateProvider


def test_state_provider_returns_safe_state() -> None:
    provider = DashboardStateProvider(log_root="logs")
    state = provider.load_state(force_demo=True)
    assert isinstance(state, dict)
    assert "security_badges" in state
    assert state.get("security_badges", {}).get("TRADING REAL") == "BLOCKED"
    assert state.get("demo_data") is True
