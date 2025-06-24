"""Testes adicionais para o motor."""

from core.engine import Engine


def test_run_simulation_chama_run(monkeypatch):
    chamado = {"ok": False}

    def fake_run() -> None:  # pragma: no cover - simples stub
        chamado["ok"] = True

    monkeypatch.setattr("simulator.run_simulation.run", fake_run)
    engine = Engine()
    engine.run_simulation()
    assert chamado["ok"]


def test_executar_decisao_maior_peso() -> None:
    """Escolhe a estratégia com o peso mais alto."""
    engine = Engine()

    def estrategia_1() -> str:
        return "comprar"

    def estrategia_2() -> str:
        return "vender"

    estrategias = {"estrategia_1": estrategia_1, "estrategia_2": estrategia_2}
    pesos = {"estrategia_1": 1.0, "estrategia_2": 2.0}
    resultado = engine.executar_decisao(estrategias, pesos)
    assert isinstance(resultado, str)
    assert resultado == "vender"
