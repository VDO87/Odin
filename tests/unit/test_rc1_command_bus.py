from odin_control.system_controller import SystemController


def test_command_bus_executes_supported_command() -> None:
    ctrl = SystemController(log_root="logs")
    result = ctrl.execute("START_ODIN", actor="test", role="operator")
    assert result["accepted"] is True


def test_command_bus_rejects_unsupported_command() -> None:
    ctrl = SystemController(log_root="logs")
    result = ctrl.execute("UNKNOWN", actor="test", role="operator")
    assert result["accepted"] is False
    assert result["reason"] == "unsupported_command"
