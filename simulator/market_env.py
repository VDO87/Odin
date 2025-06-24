"""Ambiente de mercado simplificado."""

from typing import Tuple
import numpy as np


class MarketEnv:
    """Ambiente que devolve observações de mercado."""

    def __init__(self, dados: np.ndarray) -> None:
        if dados.size == 0:
            raise ValueError("Dados de mercado vazios")
        self.dados = dados
        self.indice = 0

    def reset(self) -> float:
        """Reinicia o ambiente."""
        self.indice = 0
        return float(self.dados[self.indice])

    def step(self) -> Tuple[float, bool]:
        """Avança um passo e devolve o valor e se terminou."""
        self.indice += 1
        terminado = self.indice >= len(self.dados)
        valor = float(self.dados[min(self.indice, len(self.dados) - 1)])
        return valor, terminado
