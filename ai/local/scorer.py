"""Pontuação adaptativa para avaliação de estratégias."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class Scorer:
    """Calcula a pontuação com base em lucro e decaimento temporal."""

    def __init__(self, pesos_path: str = "pesos.json") -> None:
        self.pesos_path = Path(pesos_path)
        if self.pesos_path.exists():
            with self.pesos_path.open("r", encoding="utf-8") as f:
                self.pesos = json.load(f)
        else:
            self.pesos = {}

    def score(self, lucro: float, contexto: str) -> float:
        """Devolve uma pontuação ponderada."""
        peso_contexto = self.pesos.get(contexto, 1.0)
        decaimento = 1 / (1 + (datetime.now().timestamp() / 1e6))
        return lucro * peso_contexto * decaimento

    def guardar_pesos(self) -> None:
        """Guarda os pesos num ficheiro JSON."""
        with self.pesos_path.open("w", encoding="utf-8") as f:
            json.dump(self.pesos, f, ensure_ascii=False, indent=2)

    def atualizar_peso(self, contexto: str, valor: float) -> None:
        """Atualiza o peso de um contexto."""
        self.pesos[contexto] = valor
        self.guardar_pesos()
