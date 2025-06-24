"""Desenha a evolução dos pesos."""

import json
from pathlib import Path

import matplotlib.pyplot as plt


def plotar(pesos_path: str = "pesos.json") -> None:
    """Lê o ficheiro de pesos e plota-os."""
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
    plt.show()


if __name__ == "__main__":
    plotar()
