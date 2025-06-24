"""Entrypoint para o Odin Zero."""

import argparse
from core.engine import Engine


def parse_args() -> argparse.Namespace:
    """Processa argumentos de linha de comandos."""
    parser = argparse.ArgumentParser(description="Odin Zero")
    parser.add_argument(
        "--simular",
        action="store_true",
        help="Corre simulacoes",
    )
    return parser.parse_args()


def main() -> None:
    """Executa o Odin Zero."""
    args = parse_args()
    engine = Engine()
    if args.simular:
        engine.run_simulation()
    else:
        print("Iniciação completa do Odin Zero")


if __name__ == "__main__":
    main()
