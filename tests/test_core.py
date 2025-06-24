"""Testes para o core."""

from core.engine import Engine


def test_engine_loggers() -> None:
    engine = Engine()
    assert engine.logger_decisoes
    assert engine.logger_erros
    assert engine.logger_perf
