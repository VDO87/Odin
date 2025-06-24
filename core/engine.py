"""Motor principal do Odin Zero."""

import logging
from pathlib import Path


class Engine:
    """Classe principal que gere o sistema."""

    def __init__(self) -> None:
        self._configurar_logging()

    def _configurar_logging(self) -> None:
        """Configura os loggers para decisões, erros e performance."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        self.logger_decisoes = logging.getLogger("decisoes")
        self.logger_erros = logging.getLogger("erros")
        self.logger_perf = logging.getLogger("performance")

        self.logger_decisoes.setLevel(logging.INFO)
        self.logger_erros.setLevel(logging.ERROR)
        self.logger_perf.setLevel(logging.INFO)

        fmt = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
        )

        fh_decisoes = logging.FileHandler(log_dir / "decisoes.log")
        fh_decisoes.setFormatter(fmt)
        self.logger_decisoes.addHandler(fh_decisoes)

        fh_erros = logging.FileHandler(log_dir / "erros.log")
        fh_erros.setFormatter(fmt)
        self.logger_erros.addHandler(fh_erros)

        fh_perf = logging.FileHandler(log_dir / "performance.log")
        fh_perf.setFormatter(fmt)
        self.logger_perf.addHandler(fh_perf)

    def run_simulation(self) -> None:
        """Executa uma simulação simples."""
        try:
            from simulator.run_simulation import run

            self.logger_decisoes.info("Início da simulação")
            run()
            self.logger_perf.info("Simulação terminada")
        except Exception as exc:  # noqa: BLE001
            self.logger_erros.error("Erro na simulação: %s", exc)
            raise
