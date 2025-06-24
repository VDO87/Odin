"""Estratégias de exemplo."""


def rsi_buy_strategy(rsi: float) -> str:
    """Retorna 'comprar' se RSI < 30, caso contrário 'nada'."""
    return "comprar" if rsi < 30 else "nada"


def macd_cross_strategy(macd: float, signal: float) -> str:
    """Retorna 'comprar' se MACD > signal, senão 'vender'."""
    return "comprar" if macd > signal else "vender"
