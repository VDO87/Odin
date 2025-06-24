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
