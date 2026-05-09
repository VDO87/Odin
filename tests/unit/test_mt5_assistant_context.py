from odin_assistant.assistant_router import AssistantRouter, MT5_UNAVAILABLE_MSG
from odin_control.system_controller import SystemController


def test_assistant_reports_mt5_unavailable_safely() -> None:
    controller = SystemController(log_root="logs")
    assistant = AssistantRouter(controller)
    result = assistant.ask("O MT5 está ligado?", channel="dashboard")
    assert result["answer"] in {MT5_UNAVAILABLE_MSG, "{'shadow_mode': True}"} or "MT5" in result["answer"]
