"""JSONL audit logger."""

from __future__ import annotations

import json
from pathlib import Path

from odin.contracts.events import OdinEvent


class JsonlLogger:
    def __init__(self, path: Path | str = "logs/odin_events.jsonl") -> None:
        self.path = Path(path)

    def initialize(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        return self.path.exists() and self.path.is_file()

    def write(self, event: OdinEvent) -> None:
        self.initialize()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")

