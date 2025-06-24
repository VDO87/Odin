"""Testes para as estratégias."""

from strategies.rsi import signal as rsi
from strategies.macd import signal as macd
from strategies.ema import signal as ema
from strategies.bollinger import signal as bollinger


def test_rsi() -> None:
    assert rsi(80) == "VENDA"
    assert rsi(20) == "COMPRA"


def test_macd() -> None:
    assert macd(1) == "COMPRA"
    assert macd(-1) == "VENDA"


def test_ema() -> None:
    assert ema(2) == "COMPRA"
    assert ema(-2) == "VENDA"


def test_bollinger() -> None:
    assert bollinger(3) == "VENDA"
    assert bollinger(-3) == "COMPRA"
