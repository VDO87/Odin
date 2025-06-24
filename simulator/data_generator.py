"""Gera dados de mercado sintéticos."""

import numpy as np
import pandas as pd


def gerar_dados(
    num_pontos: int = 100,
    cenario: str = "lateral",
) -> pd.DataFrame:
    """Gera uma série temporal simulada.

    Parameters
    ----------
    num_pontos : int
        Quantidade de pontos a gerar.
    cenario : str
        Tipo de cenário: ``"tendencial"``, ``"lateral"`` ou
        ``"volatilidade_alta"``.
    """

    if num_pontos <= 0:
        raise ValueError("num_pontos deve ser positivo")

    if cenario == "tendencial":
        tendencia = np.linspace(100, 150, num_pontos)
        ruido = np.random.normal(0, 1, num_pontos)
        precos = tendencia + np.cumsum(ruido)
    elif cenario == "volatilidade_alta":
        precos = np.cumsum(np.random.normal(0, 5, num_pontos)) + 100
    else:  # lateral
        precos = 100 + np.random.normal(0, 1, num_pontos)

    return pd.DataFrame({"preco": precos})


if __name__ == "__main__":
    print(gerar_dados(5))
