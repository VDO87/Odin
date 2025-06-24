"""Geração de gráfico de evolução de pesos."""

import json
from pathlib import Path

import matplotlib.pyplot as plt


def plotar(
    pesos_path: str = "pesos.json",
    img_path: str = "grafico_pesos.png",
    mostrar: bool = False,
) -> None:
    """Lê o ficheiro de pesos e salva um gráfico.

    Parameters
    ----------
    pesos_path : str
        Caminho para o JSON com os pesos.
    img_path : str
        Ficheiro onde o gráfico será guardado.
    mostrar : bool, optional
        Se ``True`` exibe o gráfico na tela. O padrão é ``False``.
    """
    caminho = Path(pesos_path)
    if not caminho.exists():
        raise FileNotFoundError(pesos_path)
    with caminho.open("r", encoding="utf-8") as f:
        pesos = json.load(f)
    if not isinstance(pesos, dict):
        raise ValueError("JSON de pesos inválido: esperado objeto com pares chave/valor")

    plt.figure()
    plt.bar(pesos.keys(), pesos.values())
    plt.ylabel("Peso")
    plt.xlabel("Contexto")
    plt.title("Evolução dos Pesos")
    plt.savefig(img_path)
    if mostrar:
        plt.show()
    plt.close()


if __name__ == "__main__":
    plotar()
