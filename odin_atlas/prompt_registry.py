from __future__ import annotations

from pathlib import Path


class PromptRegistry:
    def __init__(self, root: str | Path = "odin_assistant/prompts") -> None:
        self.root = Path(root)

    def get(self, name: str) -> str:
        path = self.root / name
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")
