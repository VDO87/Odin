"""Corre a simulação de mercado com IA local."""

from typing import List

import numpy as np

from ai.local.adaptive_ai import AdaptiveAI
from simulator.data_generator import gerar_dados
from simulator.market_env import MarketEnv
from strategies.rsi import signal as rsi_signal


def run() -> None:
    """Executa a simulação simples."""
    dados = gerar_dados(50)
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
    run()
