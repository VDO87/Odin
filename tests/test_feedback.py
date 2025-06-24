"""Testes para o módulo de feedback."""

from feedback import gerar_feedback


def test_gerar_feedback_lucro_positivo() -> None:
    """Verifica se gerar_feedback devolve dicionário correto com lucro positivo."""
    fb = gerar_feedback("COMPRA", 1.0)
    assert fb == {"decisao": "COMPRA", "lucro": 1.0}


def test_gerar_feedback_lucro_negativo() -> None:
    """Verifica se gerar_feedback devolve dicionário correto com lucro negativo."""
    fb = gerar_feedback("VENDA", -2.5)
    assert fb == {"decisao": "VENDA", "lucro": -2.5}


def test_gerar_feedback_lucro_zero() -> None:
    """Verifica se gerar_feedback devolve dicionário correto com lucro zero."""
    fb = gerar_feedback("MANTER", 0.0)
    assert fb == {"decisao": "MANTER", "lucro": 0.0}


def test_gerar_feedback_entradas_invalidas() -> None:
    """Garante comportamento previsível com entradas de tipos incorretos."""
    fb = gerar_feedback(123, "lucro")
    assert fb == {"decisao": 123, "lucro": "lucro"}
