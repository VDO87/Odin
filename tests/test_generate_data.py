"""Testes para o gerador de dados."""

import pandas as pd
import pytest

from simulator.data_generator import gerar_dados as gerar_df
from simulator.generate_data import gerar_dados


def test_gerar_dados_dataframe():
    """Gera DataFrame com tamanho correto."""
    df = gerar_df(5)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5


def test_gerar_dados_invalido():
    """Falha quando ``num_pontos`` é inválido."""
    with pytest.raises(ValueError):
        gerar_df(0)


def test_generate_data_formato_e_intervalos():
    """Listas devem ter o mesmo tamanho e valores esperados."""
    n = 10
    dados = gerar_dados(n)
    assert set(dados.keys()) == {"rsi", "macd", "signal", "preco"}
    for valores in dados.values():
        assert isinstance(valores, list)
        assert len(valores) == n
    assert all(0 <= v <= 100 for v in dados["rsi"])
    assert all(-5 <= v <= 5 for v in dados["macd"])
    assert all(-5 <= v <= 5 for v in dados["signal"])
    assert all(v > 0 for v in dados["preco"])
