from odin_assistant.question_registry import QuestionRegistry


def test_question_registry_loads_allowed_questions() -> None:
    registry = QuestionRegistry("config/question_registry.yaml")
    assert registry.is_allowed("Qual é o estado do ODIN?") is True
    assert registry.is_allowed("Pergunta fora") is False
