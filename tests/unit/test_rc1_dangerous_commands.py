from odin_control.system_controller import SystemController


def test_dangerous_commands_are_blocked() -> None:
    ctrl = SystemController(log_root="logs")
    blocked = [
        "ENABLE_REAL_TRADING",
        "DISABLE_RISK_ENGINE",
        "DIRECT_ORDER_SEND",
        "DELETE_LOGS",
        "IGNORE_POSITION_RECONCILIATION",
    ]
    for command in blocked:
        result = ctrl.execute(command, actor="test", role="operator")
        assert result["accepted"] is False
        assert result["reason"] == "dangerous_command_blocked"
