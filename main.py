"""Ciclo principal de simulação do Odin Zero."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from ai.local.adaptive_ai import AdaptiveAI
from feedback import gerar_feedback
from simulator.data_generator import gerar_dados
from strategies.rsi import signal as estrategia_rsi


def parse_args() -> argparse.Namespace:
    """Processa argumentos da linha de comandos."""
    parser = argparse.ArgumentParser(description="Odin Zero")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Ativa modo debug",
    )
    return parser.parse_args()


def ciclo_simulacao() -> None:
    """Executa o ciclo completo de simulação."""
    dados = gerar_dados(30)
    ia = AdaptiveAI()
    historico = []

    for preco in dados["preco"]:
        decisao = estrategia_rsi(float(preco))
        historico.append(gerar_feedback(decisao, float(preco)))

    ia.treinar(historico)
    ia.guardar()

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    with (log_dir / "historico.log").open("a", encoding="utf-8") as f:
        for evento in historico:
            f.write(f"{datetime.now().isoformat()} {json.dumps(evento)}\n")


def main() -> None:
    """Função principal."""
    parse_args()
    ciclo_simulacao()


if __name__ == "__main__":
    main()
