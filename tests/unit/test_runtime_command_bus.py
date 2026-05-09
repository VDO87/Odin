from __future__ import annotations

from odin_control.system_controller import SystemController


def test_runtime_commands_available_via_command_bus() -> None:
    controller = SystemController(log_root="logs")
    for command in [
        "RUNTIME_STATUS",
        "RUNTIME_START",
        "RUNTIME_RUN_ONCE",
        "RUNTIME_SNAPSHOT",
        "RUNTIME_PAUSE",
        "RUNTIME_RESUME",
        "RUNTIME_STOP",
    ]:
        result = controller.execute(command, actor="test", role="system")
        assert "accepted" in result


def test_dangerous_commands_still_blocked() -> None:
    controller = SystemController(log_root="logs")
    blocked = controller.execute("DIRECT_ORDER_SEND", actor="test", role="system")
    assert blocked["accepted"] is False
