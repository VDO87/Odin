from __future__ import annotations


class AdaptivePromptOptimizer:
    def __init__(self, mode: str = "SIMULATION_ONLY") -> None:
        self.mode = mode

    def optimize(self, prompt: str) -> str:
        return prompt
