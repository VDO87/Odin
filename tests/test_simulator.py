"""Testes para o simulador."""

from simulator.data_generator import gerar_dados
from simulator.market_env import MarketEnv


def test_data_generator() -> None:
    dados = gerar_dados(10)
    assert not dados.empty


def test_market_env() -> None:
    dados = gerar_dados(5)["preco"].values
    env = MarketEnv(dados)
    assert env.reset() == float(dados[0])
    _, terminado = env.step()
    assert isinstance(terminado, bool)
