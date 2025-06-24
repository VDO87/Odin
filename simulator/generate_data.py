"""Gerador simplificado de dados de mercado."""

from __future__ import annotations

from typing import Dict, List

import numpy as np


def gerar_dados(n: int) -> Dict[str, List[float]]:
    """Gera n pontos de dados fictícios para indicadores."""
    if n <= 0:
        raise ValueError("n deve ser positivo")
    rsi = np.random.uniform(0, 100, n).tolist()
    macd = np.random.uniform(-5, 5, n).tolist()
    signal = np.random.uniform(-5, 5, n).tolist()
    preco = np.random.uniform(50, 150, n).tolist()
    return {"rsi": rsi, "macd": macd, "signal": signal, "preco": preco}
