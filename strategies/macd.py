"""Estratégia baseada no MACD."""


def signal(valor: float) -> str:
    """Retorna a decisão com base no MACD."""
    if valor > 0:
        return "COMPRA"
    if valor < 0:
        return "VENDA"
    return "AGUARDA"
