"""Testes para o módulo trainer."""

from unittest.mock import patch

from trainer import simulador_treino


def test_correr_chama_treinar() -> None:
    with patch("trainer.simulador_treino.AdaptiveAI") as MockAI:
        inst = MockAI.return_value
        simulador_treino.correr(1)
        assert inst.treinar.called
        assert inst.guardar.called
