from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from external_data.models import ExternalDataAuditRecord


class ExternalDataAuditLog:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._lock = Lock()

    def append(self, record: ExternalDataAuditRecord) -> None:
        payload = record.to_dict()
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self._file_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(payload, sort_keys=True) + "\n")
