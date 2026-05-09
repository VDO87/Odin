from __future__ import annotations


def bounded_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
