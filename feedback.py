"""Funções auxiliares de feedback para as estratégias."""

from typing import Dict


def gerar_feedback(decisao: str, lucro: float) -> Dict[str, float | str]:
    """Cria um registo de feedback.

    Parameters
    ----------
    decisao : str
        A decisão tomada pela estratégia.
    lucro : float
        Resultado associado à decisão.
    """

    return {"decisao": decisao, "lucro": lucro}
