"""Read-only Hermes recommendations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HermesRecommendation:
    id: str
    severity: str
    title: str
    message: str
    read_only: bool = True
    requires_human_review: bool = True
    can_execute: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "read_only": self.read_only,
            "requires_human_review": self.requires_human_review,
            "can_execute": self.can_execute,
        }


def build_read_only_recommendations(state: dict[str, object]) -> list[dict[str, object]]:
    return [
        HermesRecommendation(
            id="HERMES-RO-001",
            severity="INFO",
            title="Manter trading real bloqueado.",
            message=(
                "O estado actual declara real_trading=false; manter este bloqueio ate haver "
                "revisao humana e controlos formais."
            ),
        ).to_dict(),
        HermesRecommendation(
            id="HERMES-RO-002",
            severity="INFO",
            title="Continuar validacao por logs antes de integrar MT5.",
            message=(
                "A fase actual deve privilegiar auditoria JSONL e SQLite antes de qualquer "
                "adaptador operacional."
            ),
        ).to_dict(),
        HermesRecommendation(
            id="HERMES-RO-003",
            severity="INFO",
            title="Hermes esta em modo READ_ONLY.",
            message=f"Hermes permanece em {state['hermes_mode']} e nao altera risco, dinheiro ou execucao.",
        ).to_dict(),
    ]

