"""Testes para a classe AdaptiveAI."""

import json

from ai.local.adaptive_ai import AdaptiveAI


def test_adaptive_ai_treino_atualiza_pesos(tmp_path) -> None:
    """Garante que os pesos mudam conforme lucro e perda."""
    caminho = tmp_path / "pesos.json"
    ia = AdaptiveAI(pesos_path=str(caminho))
    historico = [
        {"contexto": "ganho", "lucro": 5.0},
        {"contexto": "perda", "lucro": -3.0},
    ]
    ia.treinar(historico)
    pesos = ia.scorer.pesos
    assert pesos["ganho"] > 0
    assert pesos["perda"] < 0


def test_adaptive_ai_guardar_cria_ficheiro(tmp_path) -> None:
    """Verifica que guardar escreve o JSON de pesos."""
    caminho = tmp_path / "pesos.json"
    ia = AdaptiveAI(pesos_path=str(caminho))
    ia.treinar([{"contexto": "abc", "lucro": 2.0}])
    ia.guardar()
    assert caminho.exists()
    with caminho.open("r", encoding="utf-8") as f:
        dados = json.load(f)
    assert dados.get("abc") == ia.scorer.pesos.get("abc")


def test_adaptive_ai_pesos_iniciais(tmp_path) -> None:
    """Garante que uma nova instância começa sem pesos."""
    caminho = tmp_path / "pesos.json"
    ia = AdaptiveAI(pesos_path=str(caminho))
    assert ia.scorer.pesos == {}
