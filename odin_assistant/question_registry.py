from __future__ import annotations

from pathlib import Path


class QuestionRegistry:
    def __init__(self, path: str | Path = "config/question_registry.yaml") -> None:
        self.path = Path(path)
        self.allowed_questions = self._load()

    def _load(self) -> set[str]:
        if not self.path.exists():
            return set()
        allowed: set[str] = set()
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("-"):
                allowed.add(line[1:].strip())
        return allowed

    def is_allowed(self, question: str) -> bool:
        normalized = question.strip()
        return normalized in self.allowed_questions
