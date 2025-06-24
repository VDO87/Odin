"""Testes para plot_pesos."""

import json

import pytest
import matplotlib

matplotlib.use("Agg")

from metrics import plot_pesos


def test_plotar_cria_grafico(tmp_path):
    """Verifica se a imagem é criada corretamente."""
    pesos = {"rsi": 1.5, "macd": 2.0}
    pesos_path = tmp_path / "pesos.json"
    pesos_path.write_text(json.dumps(pesos), encoding="utf-8")

    img_path = tmp_path / "grafico_pesos.png"

    plot_pesos.plotar(pesos_path=str(pesos_path), img_path=str(img_path), mostrar=False)

    assert img_path.exists()


def test_plotar_erro_ao_nao_existir_pesos(tmp_path):
    """Gera FileNotFoundError quando o JSON não existe."""
    caminho_inexistente = tmp_path / "nao_existe.json"
    img_path = tmp_path / "graf.png"
    with pytest.raises(FileNotFoundError):
        plot_pesos.plotar(pesos_path=str(caminho_inexistente), img_path=str(img_path), mostrar=False)


def test_plotar_erro_json_invalido(tmp_path):
    """Dispara ValueError quando o JSON não contém um objeto."""
    pesos_path = tmp_path / "pesos.json"
    pesos_path.write_text("[1, 2, 3]", encoding="utf-8")
    img_path = tmp_path / "graf.png"
    with pytest.raises(ValueError):
        plot_pesos.plotar(pesos_path=str(pesos_path), img_path=str(img_path), mostrar=False)
