"""Persistent Hermes goals and checkpoints."""

from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_GOAL_STATES = (
    "PENDING",
    "RUNNING",
    "WAITING",
    "BLOCKED",
    "RETRYING",
    "DEGRADED",
    "COMPLETED",
    "FAILED",
    "SAFE_STOP",
)


@dataclass(frozen=True)
class HermesGoal:
    goal_id: str
    description: str
    priority: str
    status: str
    agent: str
    checkpoint: str
    started_at: str
    last_activity_at: str
    iteration_limit: int
    time_limit_seconds: int
    token_budget: int
    completion_criteria: str
    failure_criteria: str
    next_step: str

    def to_dict(self) -> dict[str, object]:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "agent": self.agent,
            "checkpoint": self.checkpoint,
            "started_at": self.started_at,
            "last_activity_at": self.last_activity_at,
            "iteration_limit": self.iteration_limit,
            "time_limit_seconds": self.time_limit_seconds,
            "token_budget": self.token_budget,
            "completion_criteria": self.completion_criteria,
            "failure_criteria": self.failure_criteria,
            "next_step": self.next_step,
        }


def bootstrap_supervisor_goal(timestamp: str) -> HermesGoal:
    return HermesGoal(
        goal_id="hermes_operational_supervision",
        description="Tornar o Hermes supervisor local-first do projeto sem desbloquear trading real.",
        priority="HIGH",
        status="RUNNING",
        agent="hermes_supervisor",
        checkpoint="bootstrap",
        started_at=timestamp,
        last_activity_at=timestamp,
        iteration_limit=12,
        time_limit_seconds=3600,
        token_budget=6000,
        completion_criteria="Supervisor, memoria, goals, skills e routing local-first operacionais em modo seguro.",
        failure_criteria="Perda de memoria persistente, risco desbloqueado, loop sem progresso ou dependencia critica ausente.",
        next_step="Verificar provider local, skills e estado do Odin.",
    )
