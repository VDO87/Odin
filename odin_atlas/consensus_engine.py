from __future__ import annotations

from typing import Any

from odin_atlas.confidence_scoring import bounded_score


class ConsensusEngine:
    def __init__(self, min_consensus_score: float = 0.65) -> None:
        self.min_consensus_score = min_consensus_score

    def score(self, agent_scores: dict[str, float]) -> float:
        if not agent_scores:
            return 0.0
        return bounded_score(sum(agent_scores.values()) / len(agent_scores))

    def evaluate(self, agent_scores: dict[str, float]) -> dict[str, Any]:
        score = self.score(agent_scores)
        return {
            "consensus_score": score,
            "accepted": score >= self.min_consensus_score,
            "reason": "consensus_ok" if score >= self.min_consensus_score else "consensus_below_threshold",
        }
