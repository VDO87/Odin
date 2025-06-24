"""Testes para o módulo de feedback."""

from feedback import gerar_feedback


def test_gerar_feedback():
    fb = gerar_feedback("COMPRA", 1.0)
    assert fb == {"decisao": "COMPRA", "lucro": 1.0}
