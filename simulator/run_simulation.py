"""Corre a simulação de mercado com IA local."""

from typing import List

import numpy as np

from ai.local.adaptive_ai import AdaptiveAI
from simulator.data_generator import gerar_dados
from simulator.market_env import MarketEnv
from strategies.rsi import signal as rsi_signal


def run(cenario: str = "lateral") -> None:
    """Executa a simulação simples para o ``cenario`` escolhido."""
    dados = gerar_dados(50, cenario=cenario)
    env = MarketEnv(dados["preco"].values)
    ia = AdaptiveAI()
    historico: List[dict] = []

    obs = env.reset()
    terminado = False
    while not terminado:
        acao = rsi_signal(obs)
        lucro = np.random.randn()  # placeholder para cálculo real
        historico.append({"contexto": acao, "lucro": lucro})
        obs, terminado = env.step()

    ia.treinar(historico)
    ia.guardar()
    print("Simulação concluída")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simulação Odin Zero")
    parser.add_argument(
        "--cenario",
        choices=["tendencial", "lateral", "volatilidade_alta"],
        default="lateral",
        help="Tipo de cenário da simulação",
    )
    args = parser.parse_args()
    run(args.cenario)
