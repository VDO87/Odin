from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_llm_installation_readiness_docs_and_service_example() -> None:
    runbook = ROOT / "docs/runbooks/LLM_INSTALLATION_READINESS.md"
    override = ROOT / "services/ollama-override.example"
    assert runbook.exists()
    assert override.exists()
    text = runbook.read_text(encoding="utf-8").lower()
    assert "não instala modelos automaticamente" in text
    assert "openai" in text
    override_text = override.read_text(encoding="utf-8")
    assert "OLLAMA_MODELS" in override_text
