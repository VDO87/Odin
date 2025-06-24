"""Testes para o gerador de dados."""

import pandas as pd
import pytest

from simulator.data_generator import gerar_dados


def test_gerar_dados_tamanho():
    df = gerar_dados(5)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5


def test_gerar_dados_invalido():
    with pytest.raises(ValueError):
        gerar_dados(0)
