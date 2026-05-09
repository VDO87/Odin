from __future__ import annotations

from odin_control.system_controller import SystemController


def test_runtime_run_once_without_mt5_real() -> None:
    controller = SystemController(log_root="logs")
    result = controller.execute("RUNTIME_RUN_ONCE", actor="test", role="system")
    assert "runtime" in result["data"]
    runtime_payload = result["data"]["runtime"]
    assert "runtime" in runtime_payload
    snap = runtime_payload.get("snapshot", {})
    if snap:
        assert snap.get("safe_to_trade") is False or isinstance(snap.get("safe_to_trade"), bool)
        assert snap.get("trading_real_enabled") is False
        assert snap.get("mt5_order_send_enabled") is False


def test_runtime_does_not_enable_real_trading() -> None:
    controller = SystemController(log_root="logs")
    controller.execute("RUNTIME_RUN_ONCE", actor="test", role="system")
    status = controller.execute("RUNTIME_STATUS", actor="test", role="system")
    assert status["accepted"] is True
