from __future__ import annotations

from odin_assistant.assistant_router import AssistantRouter
from odin_control.system_controller import SystemController


def test_assistant_valid_question_uses_fallback_or_llm(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")
    controller = SystemController(log_root="logs")
    assistant = AssistantRouter(controller)

    result = assistant.ask("Qual é o estado do ODIN?", channel="cli")
    assert "answer" in result
    assert result["source"] in {"fallback", "local_llm"}
    assert "question_id" in result


def test_assistant_blocks_out_of_scope() -> None:
    controller = SystemController(log_root="logs")
    assistant = AssistantRouter(controller)
    result = assistant.ask("Qual é a capital de França?", channel="cli")
    assert result["status"] == "BLOCKED"


def test_assistant_blocks_dangerous_request() -> None:
    controller = SystemController(log_root="logs")
    assistant = AssistantRouter(controller)
    result = assistant.ask("Activa trading real", channel="cli")
    assert result["status"] == "BLOCKED"
    assert "bloqueado" in result["answer"].lower()
