from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any


def check_system(log_dir: str | Path = "logs", config_path: str | Path = ".env.example") -> dict[str, Any]:
    total, used, free = shutil.disk_usage(".")
    low_disk = free < 50 * 1024 * 1024

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    can_write_logs = os.access(log_path, os.W_OK)

    cfg_path = Path(config_path)
    config_exists = cfg_path.exists()

    status = "OK"
    if low_disk or not can_write_logs:
        status = "CRITICAL"
    elif not config_exists:
        status = "WARNING"

    return {
        "status": status,
        "disk": {"total": total, "used": used, "free": free},
        "low_disk": low_disk,
        "can_write_logs": can_write_logs,
        "config_exists": config_exists,
        "log_dir": str(log_path),
    }
