from __future__ import annotations

from odin_assistant.assistant_router import AssistantRouter
from odin_control.system_controller import SystemController


def test_assistant_answers_runtime_questions() -> None:
    controller = SystemController(log_root="logs")
    controller.execute("RUNTIME_RUN_ONCE", actor="test", role="system")
    assistant = AssistantRouter(controller)

    result = assistant.ask("Qual é o estado runtime do ODIN?", channel="cli")
    assert "answer" in result

    result2 = assistant.ask("Mostra o snapshot actual.", channel="cli")
    assert "answer" in result2
