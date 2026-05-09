from odin_execution.mt5_shadow import MT5ShadowAdapter


def test_mt5_shadow_adapter_unavailable_does_not_crash() -> None:
    adapter = MT5ShadowAdapter(order_send_enabled=False)
    health = adapter.healthcheck()
    assert "status" in health
    assert "message" in health
    assert "safe_to_trade" in health


def test_mt5_shadow_place_order_is_blocked() -> None:
    adapter = MT5ShadowAdapter(order_send_enabled=False)
    result = adapter.place_order({"symbol": "EURUSD"})
    assert result["status"] == "BLOCKED"
    assert "bloqueado" in result["message"].lower()
