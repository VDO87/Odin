from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _expand(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


@dataclass(frozen=True)
class DeployPaths:
    odin_home: Path
    app_dir: Path
    venv_dir: Path
    config_dir: Path
    data_dir: Path
    log_dir: Path
    models_dir: Path
    vendor_dir: Path
    backup_dir: Path
    tmp_dir: Path
    dashboard_preview_dir: Path
    services_dir: Path
    dist_dir: Path

    @property
    def env_file(self) -> Path:
        return self.config_dir / ".env"

    @property
    def env_example_file(self) -> Path:
        return self.config_dir / ".env.example"

    def required_dirs(self) -> list[Path]:
        return [
            self.odin_home,
            self.app_dir,
            self.venv_dir,
            self.config_dir,
            self.data_dir,
            self.data_dir / "runtime",
            self.data_dir / "memory",
            self.data_dir / "market",
            self.data_dir / "backtests",
            self.data_dir / "soak_tests",
            self.log_dir,
            self.log_dir / "system",
            self.log_dir / "health",
            self.log_dir / "control",
            self.log_dir / "assistant",
            self.log_dir / "atlas",
            self.log_dir / "market",
            self.log_dir / "trading",
            self.log_dir / "telegram",
            self.log_dir / "brokers",
            self.log_dir / "errors",
            self.models_dir,
            self.models_dir / "ollama",
            self.vendor_dir,
            self.vendor_dir / "wheels",
            self.vendor_dir / "atlas",
            self.vendor_dir / "llm",
            self.services_dir,
            self.backup_dir,
            self.dist_dir,
            self.dashboard_preview_dir,
            self.tmp_dir,
        ]

    def as_env(self) -> dict[str, str]:
        return {
            "ODIN_HOME": str(self.odin_home),
            "ODIN_APP_DIR": str(self.app_dir),
            "ODIN_CONFIG_DIR": str(self.config_dir),
            "ODIN_DATA_DIR": str(self.data_dir),
            "ODIN_LOG_DIR": str(self.log_dir),
            "ODIN_MODELS_DIR": str(self.models_dir),
            "ODIN_VENDOR_DIR": str(self.vendor_dir),
            "ODIN_BACKUP_DIR": str(self.backup_dir),
            "ODIN_TMP_DIR": str(self.tmp_dir),
            "ODIN_DASHBOARD_PREVIEW_DIR": str(self.dashboard_preview_dir),
        }


def resolve_deploy_paths(odin_home: str | None = None) -> DeployPaths:
    default_home = os.getenv("ODIN_HOME") or "~/ODIN_RUNTIME"
    resolved_home = _expand(odin_home or default_home)
    return DeployPaths(
        odin_home=resolved_home,
        app_dir=resolved_home / "app",
        venv_dir=resolved_home / ".venv",
        config_dir=resolved_home / "config",
        data_dir=resolved_home / "data",
        log_dir=resolved_home / "logs",
        models_dir=resolved_home / "models",
        vendor_dir=resolved_home / "vendor",
        backup_dir=resolved_home / "backups",
        tmp_dir=resolved_home / "tmp",
        dashboard_preview_dir=resolved_home / "dashboard_preview",
        services_dir=resolved_home / "services",
        dist_dir=resolved_home / "dist",
    )
