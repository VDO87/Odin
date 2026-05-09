from __future__ import annotations

from odin_dashboard.state_provider import DashboardStateProvider, _risk_block_reasons


def test_risk_block_reasons_are_clean_and_actionable() -> None:
    state = DashboardStateProvider(log_root="logs").load_state(force_demo=True)
    risk = state.get("risk", {})
    assert isinstance(risk, dict)
    reasons = risk.get("blocked_reasons")
    assert isinstance(reasons, list)
    joined = " ".join(str(item) for item in reasons).lower()
    assert "network_ok" not in joined
    assert "no active risk block detected" not in joined


def test_risk_default_reason_when_no_active_block() -> None:
    reasons = _risk_block_reasons(
        safe_to_trade=True,
        health_state="OK",
        mt5_state="OK",
        runtime_validate_state="OK",
        security={
            "broker_real_blocked": True,
            "mt5_order_send_blocked": True,
            "trading_real_blocked": True,
        },
    )
    assert reasons == ["No active risk block detected"]
