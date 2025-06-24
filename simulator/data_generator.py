"""Gera dados de mercado sintéticos."""

import numpy as np
import pandas as pd


def gerar_dados(num_pontos: int = 100) -> pd.DataFrame:
    """Gera uma série temporal simulada."""
    if num_pontos <= 0:
        raise ValueError("num_pontos deve ser positivo")
    precos = np.cumsum(np.random.randn(num_pontos)) + 100
    return pd.DataFrame({"preco": precos})


if __name__ == "__main__":
    print(gerar_dados(5))
