"""Pipeline de treino para IA local."""

from typing import Any, Dict, List

from ai.local.scorer import Scorer


class AdaptiveAI:
    """Treina e guarda pesos de forma adaptativa."""

    def __init__(self, pesos_path: str = "pesos.json") -> None:
        self.scorer = Scorer(pesos_path)

    def treinar(self, historico: List[Dict[str, Any]]) -> None:
        """Atualiza pesos com base no histórico."""
        for registo in historico:
            contexto = registo.get("contexto", "default")
            lucro = float(registo.get("lucro", 0))
            pontuacao = self.scorer.score(lucro, contexto)
            self.scorer.atualizar_peso(contexto, pontuacao)

    def guardar(self) -> None:
        """Guarda os pesos."""
        self.scorer.guardar_pesos()
