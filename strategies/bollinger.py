"""Estratégia baseada em Bandas de Bollinger."""


def signal(valor: float) -> str:
    """Decide com base nas bandas."""
    if valor > 2:
        return "VENDA"
    if valor < -2:
        return "COMPRA"
    return "AGUARDA"
