"""Estratégia baseada na Média Exponencial."""


def signal(valor: float) -> str:
    """Decide com base na Média Exponencial."""
    if valor > 1:
        return "COMPRA"
    if valor < -1:
        return "VENDA"
    return "AGUARDA"
