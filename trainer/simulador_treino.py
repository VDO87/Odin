"""Ferramenta para treino offline das estratégias."""

from ai.local.adaptive_ai import AdaptiveAI
from simulator.data_generator import gerar_dados


def correr(num_iter: int = 10) -> None:
    """Executa várias simulações para treino."""
    ia = AdaptiveAI()
    for _ in range(num_iter):
        dados = gerar_dados(20)
        linhas = []
        for preco in dados["preco"]:
            linhas.append({"contexto": "treino", "lucro": float(preco)})
        ia.treinar(linhas)
    ia.guardar()


if __name__ == "__main__":
    correr()
