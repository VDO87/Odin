from __future__ import annotations

import odin_health.checks_mt5 as checks_mt5


class _UnavailableAdapter:
    def __init__(self, order_send_enabled: bool = False) -> None:
        self.order_send_enabled = order_send_enabled

    def is_available(self) -> bool:
        return False


def test_mt5_healthcheck_blocks_shadow_mode_when_mt5_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("ODIN_MODE", "SHADOW_MT5")
    monkeypatch.setenv("MT5_ENABLED", "true")
    monkeypatch.setenv("MT5_ORDER_SEND_ENABLED", "false")
    monkeypatch.setattr(checks_mt5, "MT5ShadowAdapter", _UnavailableAdapter)

    result = checks_mt5.check_mt5()
    assert result["status"] == "BLOCKED"
    assert result["safe_to_trade"] is False
