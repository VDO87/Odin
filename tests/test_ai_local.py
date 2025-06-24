"""Testes para IA local."""

from ai.local.scorer import Scorer
from ai.local.adaptive_ai import AdaptiveAI


def test_scorer(tmp_path) -> None:
    arquivo = tmp_path / "pesos.json"
    scorer = Scorer(pesos_path=str(arquivo))
    pontuacao = scorer.score(10, "teste")
    assert isinstance(pontuacao, float)
    scorer.atualizar_peso("teste", pontuacao)
    assert "teste" in scorer.pesos


def test_adaptive_ai_treinar(tmp_path) -> None:
    arquivo = tmp_path / "pesos.json"
    ia = AdaptiveAI(pesos_path=str(arquivo))
    historico = [{"contexto": "ctx", "lucro": 5.0}]
    ia.treinar(historico)
    ia.guardar()
    assert arquivo.exists()
