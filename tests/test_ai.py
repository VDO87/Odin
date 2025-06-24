"""Testes para IA local."""

from ai.local.scorer import Scorer


def test_scorer() -> None:
    scorer = Scorer(pesos_path="test_pesos.json")
    pontuacao = scorer.score(10, "teste")
    assert isinstance(pontuacao, float)
    scorer.atualizar_peso("teste", pontuacao)
    assert "teste" in scorer.pesos
