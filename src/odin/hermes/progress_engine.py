"""Motor persistente de progresso e escalamento do Hermes."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    LOCAL_EXECUTION = "LOCAL_EXECUTION"
    TESTING = "TESTING"
    LOCAL_RETRY = "LOCAL_RETRY"
    CODEX_REVIEW = "CODEX_REVIEW"
    BLOCKED = "BLOCKED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED_SAFE = "FAILED_SAFE"


class ProgressAction(StrEnum):
    CONTINUE = "continue"
    RETRY_LOCAL = "retry_local"
    ESCALATE_CODEX = "escalate_codex"


@dataclass(frozen=True)
class ProgressSnapshot:
    tests_passed: int = 0
    tests_failed: int = 0
    coverage_percent: float | None = None
    lint_errors: int = 0
    type_errors: int = 0
    changed_files: tuple[str, ...] = ()
    diff_lines: int = 0
    error_signature: str | None = None
    out_of_scope_files: tuple[str, ...] = ()
    regressions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        counts = (
            self.tests_passed,
            self.tests_failed,
            self.lint_errors,
            self.type_errors,
            self.diff_lines,
        )
        if any(value < 0 for value in counts):
            raise ValueError("metricas de progresso nao podem ser negativas")
        if self.coverage_percent is not None and not 0 <= self.coverage_percent <= 100:
            raise ValueError("coverage_percent deve estar entre 0 e 100")


@dataclass(frozen=True)
class ProgressDecision:
    action: ProgressAction
    improved: bool
    reasons: tuple[str, ...]


@dataclass
class TaskState:
    task_id: str
    objective: str
    acceptance_criteria: list[str]
    allowed_paths: list[str]
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    no_progress_attempts: int = 0
    current_error: str | None = None
    error_signature: str | None = None
    changed_files: list[str] = field(default_factory=list)
    latest_snapshot: dict[str, Any] | None = None
    next_action: str = "plan"
    checkpoint: str | None = None
    escalation_history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.task_id.strip() or not self.objective.strip():
            raise ValueError("task_id e objective sao obrigatorios")


class ProgressEngine:
    """Decide por metricas; nunca aceita a declaracao do modelo como prova."""

    def __init__(
        self,
        *,
        max_no_progress_attempts: int = 2,
        max_local_attempts: int = 3,
        max_diff_growth_percent: float = 20.0,
    ) -> None:
        if max_no_progress_attempts < 1 or max_local_attempts < 1:
            raise ValueError("limites de tentativas devem ser positivos")
        self.max_no_progress_attempts = max_no_progress_attempts
        self.max_local_attempts = max_local_attempts
        self.max_diff_growth_percent = max_diff_growth_percent

    def evaluate(
        self,
        *,
        previous: ProgressSnapshot | None,
        current: ProgressSnapshot,
        local_attempt: int,
        no_progress_attempts: int,
        critical_change: bool = False,
    ) -> ProgressDecision:
        immediate: list[str] = []
        if critical_change:
            immediate.append("critical_change")
        if current.out_of_scope_files:
            immediate.append("out_of_scope_files")
        if current.regressions:
            immediate.append("regressions_detected")
        if (
            previous is not None
            and current.error_signature
            and current.error_signature == previous.error_signature
        ):
            immediate.append("repeated_error_signature")
        if immediate:
            return ProgressDecision(ProgressAction.ESCALATE_CODEX, False, tuple(immediate))

        improved, reasons = _compare_progress(previous, current, self.max_diff_growth_percent)
        if improved:
            return ProgressDecision(ProgressAction.CONTINUE, True, tuple(reasons))

        exhausted = local_attempt >= self.max_local_attempts
        stalled = no_progress_attempts + 1 >= self.max_no_progress_attempts
        if exhausted or stalled:
            escalation_reasons = list(reasons) or ["no_objective_improvement"]
            if exhausted:
                escalation_reasons.append("max_local_attempts")
            if stalled:
                escalation_reasons.append("max_no_progress_attempts")
            return ProgressDecision(
                ProgressAction.ESCALATE_CODEX,
                False,
                tuple(escalation_reasons),
            )
        return ProgressDecision(
            ProgressAction.RETRY_LOCAL,
            False,
            tuple(reasons or ["no_objective_improvement"]),
        )


class TaskStateStore:
    """Guarda estado JSON de forma atomica, sem executar qualquer tarefa."""

    def __init__(self, root: str | Path = "~/hermes_state") -> None:
        self.root = Path(root).expanduser()
        self.tasks_dir = self.root / "tasks"
        self.escalations_dir = self.root / "escalations"
        self.checkpoints_dir = self.root / "checkpoints"
        for directory in (self.tasks_dir, self.escalations_dir, self.checkpoints_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def save(self, state: TaskState) -> Path:
        path = self.tasks_dir / f"{_safe_task_id(state.task_id)}.json"
        payload = asdict(state)
        payload["status"] = state.status.value
        _atomic_json_write(path, payload)
        return path

    def load(self, task_id: str) -> TaskState:
        path = self.tasks_dir / f"{_safe_task_id(task_id)}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["status"] = TaskStatus(payload["status"])
        return TaskState(**payload)

    def save_escalation(self, task_id: str, package: dict[str, object]) -> Path:
        path = self.escalations_dir / f"{_safe_task_id(task_id)}.json"
        _atomic_json_write(path, package)
        return path


def build_codex_escalation_package(
    *,
    state: TaskState,
    failed_tests: list[str],
    relevant_diff: str,
    progress_metrics: ProgressSnapshot,
    technical_question: str,
    max_diff_chars: int = 12_000,
) -> dict[str, object]:
    """Cria o contexto minimo para revisao Codex, sem incluir o repositorio inteiro."""
    if not technical_question.strip():
        raise ValueError("technical_question e obrigatoria")
    clipped_diff = relevant_diff[:max_diff_chars]
    return {
        "task_id": state.task_id,
        "objective": state.objective,
        "acceptance_criteria": state.acceptance_criteria,
        "allowed_paths": state.allowed_paths,
        "attempts": state.attempts,
        "error_signature": state.error_signature,
        "changed_files": state.changed_files,
        "failed_tests": failed_tests,
        "progress_metrics": asdict(progress_metrics),
        "relevant_diff": clipped_diff,
        "diff_truncated": len(relevant_diff) > max_diff_chars,
        "technical_question": technical_question,
    }


def _compare_progress(
    previous: ProgressSnapshot | None,
    current: ProgressSnapshot,
    max_diff_growth_percent: float,
) -> tuple[bool, list[str]]:
    if previous is None:
        return True, ["baseline_recorded"]

    improvements: list[str] = []
    if current.tests_failed < previous.tests_failed:
        improvements.append("fewer_failed_tests")
    if current.tests_passed > previous.tests_passed:
        improvements.append("more_passing_tests")
    if current.lint_errors < previous.lint_errors:
        improvements.append("fewer_lint_errors")
    if current.type_errors < previous.type_errors:
        improvements.append("fewer_type_errors")
    if (
        current.coverage_percent is not None
        and previous.coverage_percent is not None
        and current.coverage_percent > previous.coverage_percent
    ):
        improvements.append("coverage_increased")

    excessive_growth = False
    if previous.diff_lines > 0:
        growth = ((current.diff_lines - previous.diff_lines) / previous.diff_lines) * 100
        excessive_growth = growth > max_diff_growth_percent
    if excessive_growth:
        return False, ["diff_grew_without_safe_improvement"]
    return bool(improvements), improvements


def _safe_task_id(task_id: str) -> str:
    if not task_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in task_id):
        raise ValueError("task_id contem caracteres nao permitidos")
    return task_id


def _atomic_json_write(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
