from __future__ import annotations

from odin_health.checks_llm import check_local_llm


def test_llm_healthcheck_warning_when_model_missing(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_ENABLED", "true")
    monkeypatch.setenv("LOCAL_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "")
    result = check_local_llm()
    assert result["status"] == "WARNING"
    assert result["reason"] == "local_llm_model_not_configured"


def test_llm_healthcheck_disabled(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_ENABLED", "false")
    result = check_local_llm()
    assert result["status"] == "WARNING"
    assert result["reason"] == "local_llm_disabled"
