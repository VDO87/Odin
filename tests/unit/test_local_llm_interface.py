from __future__ import annotations

from odin_assistant.local_llm_interface import LocalLLMInterface


def test_local_llm_warning_when_model_missing(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_ENABLED", "true")
    monkeypatch.setenv("LOCAL_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")

    llm = LocalLLMInterface()
    health = llm.healthcheck()
    assert health["status"] == "WARNING"
    assert health["error"] == "local_llm_model_not_configured"

    result = llm.safe_answer("Qual é o estado do ODIN?", {"state": "RUNNING"})
    assert result["status"] == "WARNING"
    assert "model_not_configured" in str(result.get("error", ""))


def test_local_llm_result_shape(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_ENABLED", "false")
    llm = LocalLLMInterface()
    result = llm.safe_answer("Q", {"x": 1})
    for key in [
        "status",
        "provider",
        "model",
        "response",
        "error",
        "latency_ms",
        "used_context",
        "safe",
        "timestamp",
    ]:
        assert key in result
