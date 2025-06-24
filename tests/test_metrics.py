"""Testes para o módulo metrics."""

import json
from unittest.mock import patch

from metrics import plot_pesos


def test_plotar(tmp_path) -> None:
    caminho = tmp_path / "pesos.json"
    with caminho.open("w", encoding="utf-8") as f:
        json.dump({"a": 1, "b": 2}, f)
    img = tmp_path / "graf.png"
    with patch("matplotlib.pyplot.savefig") as mock_save:
        plot_pesos.plotar(str(caminho), str(img))
        assert mock_save.called
