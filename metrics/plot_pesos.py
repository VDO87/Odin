"""Geração de gráfico de evolução de pesos."""

import json
from pathlib import Path

import matplotlib.pyplot as plt


def plotar(
    pesos_path: str = "pesos.json",
    img_path: str = "grafico_pesos.png",
) -> None:
    """Lê o ficheiro de pesos e salva um gráfico.

    Parameters
    ----------
    pesos_path : str
        Caminho para o JSON com os pesos.
    img_path : str
        Ficheiro onde o gráfico será guardado.
    """
    caminho = Path(pesos_path)
    if not caminho.exists():
        raise FileNotFoundError(pesos_path)
    with caminho.open("r", encoding="utf-8") as f:
        pesos = json.load(f)

    plt.figure()
    plt.bar(pesos.keys(), pesos.values())
    plt.ylabel("Peso")
    plt.xlabel("Contexto")
    plt.title("Evolução dos Pesos")
    plt.savefig(img_path)
    plt.close()


if __name__ == "__main__":
    plotar()
