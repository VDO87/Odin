from odin_brokers.mt5_adapter import MT5Adapter
from odin_control.system_controller import SystemController


def test_mt5_adapter_blocks_order_and_close() -> None:
    adapter = MT5Adapter()
    place = adapter.place_order({"symbol": "EURUSD"})
    close = adapter.close_order("1")
    assert place["status"] == "BLOCKED"
    assert close["status"] == "BLOCKED"


def test_mt5_dangerous_commands_are_blocked() -> None:
    ctrl = SystemController(log_root="logs")
    for command in ["MT5_ORDER_SEND", "MT5_CLOSE_POSITION", "MT5_MODIFY_POSITION", "MT5_ENABLE_REAL_TRADING"]:
        result = ctrl.execute(command, actor="test", role="operator")
        assert result["accepted"] is False
        assert result["reason"] == "dangerous_command_blocked"
