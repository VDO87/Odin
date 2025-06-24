"""Estratégia baseada no índice RSI."""


def signal(valor: float) -> str:
    """Devolve a ação recomendada."""
    if valor > 70:
        return "VENDA"
    if valor < 30:
        return "COMPRA"
    return "AGUARDA"
