"""Ensaio controlado Hermes -> Ollama -> validadores -> revisao Codex."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import threading
import time
from queue import Empty, Queue
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from odin.hermes.progress_engine import (
    ProgressAction,
    ProgressEngine,
    ProgressSnapshot,
    TaskState,
    TaskStateStore,
    TaskStatus,
    build_codex_escalation_package,
)


ProposalProvider = Callable[[int, str | None], Mapping[str, str]]
Validator = Callable[[Path, tuple[str, ...]], "ValidationResult"]


@dataclass(frozen=True)
class ControlledTask:
    task_id: str
    objective: str
    acceptance_criteria: tuple[str, ...]
    allowed_paths: tuple[str, ...]


@dataclass(frozen=True)
class ValidationResult:
    snapshot: ProgressSnapshot
    failed_tests: tuple[str, ...] = ()
    feedback: str = ""

    @property
    def passed(self) -> bool:
        return (
            self.snapshot.tests_failed == 0
            and self.snapshot.lint_errors == 0
            and self.snapshot.type_errors == 0
            and not self.snapshot.regressions
            and not self.snapshot.out_of_scope_files
        )


@dataclass(frozen=True)
class ControlledFlowResult:
    task_id: str
    status: TaskStatus
    attempts: int
    next_action: str
    escalation_created: bool
    validation: ValidationResult


class ControlledFlow:
    """Aplica propostas apenas numa sandbox e nunca chama o Codex automaticamente."""

    def __init__(
        self,
        *,
        state_store: TaskStateStore,
        sandbox_root: str | Path,
        engine: ProgressEngine | None = None,
        validator: Validator | None = None,
        max_flow_seconds: float = 180.0,
        provider_timeout_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.state_store = state_store
        self.sandbox_root = Path(sandbox_root).resolve()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        self.engine = engine or ProgressEngine()
        self.validator = validator or validate_python_sandbox
        if max_flow_seconds <= 0 or provider_timeout_seconds <= 0:
            raise ValueError("timeouts do fluxo devem ser positivos")
        self.max_flow_seconds = max_flow_seconds
        self.provider_timeout_seconds = provider_timeout_seconds
        self._clock = clock

    def run(self, task: ControlledTask, provider: ProposalProvider) -> ControlledFlowResult:
        started = self._clock()
        workspace = (self.sandbox_root / task.task_id).resolve()
        _assert_within(workspace, self.sandbox_root)
        workspace.mkdir(parents=True, exist_ok=True)
        state = TaskState(
            task_id=task.task_id,
            objective=task.objective,
            acceptance_criteria=list(task.acceptance_criteria),
            allowed_paths=list(task.allowed_paths),
            status=TaskStatus.LOCAL_EXECUTION,
            next_action="request_local_proposal",
        )
        self.state_store.save(state)
        previous: ProgressSnapshot | None = None
        feedback: str | None = None
        latest = ValidationResult(ProgressSnapshot(), feedback="not_started")

        for attempt in range(1, self.engine.max_local_attempts + 1):
            state.attempts = attempt
            proposal: Mapping[str, str] = {}
            try:
                remaining = self.max_flow_seconds - (self._clock() - started)
                if remaining <= 0:
                    raise TimeoutError("flow_timeout")
                proposal = _call_with_timeout(
                    provider,
                    (attempt, feedback),
                    min(remaining, self.provider_timeout_seconds),
                )
                changed_files = apply_sandbox_proposal(
                    workspace=workspace,
                    proposal=proposal,
                    allowed_paths=task.allowed_paths,
                )
                state.status = TaskStatus.TESTING
                state.changed_files = list(changed_files)
                remaining = self.max_flow_seconds - (self._clock() - started)
                if remaining <= 0:
                    raise TimeoutError("flow_timeout")
                latest = _call_with_timeout(
                    self.validator,
                    (workspace, changed_files),
                    remaining,
                )
            except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
                message = f"{type(exc).__name__}: {exc}"
                signature = hashlib.sha256(message.encode()).hexdigest()[:16]
                unsafe_scope = (message,) if "fora do ambito" in message or "caminho inseguro" in message else ()
                latest = ValidationResult(
                    ProgressSnapshot(
                        tests_failed=1,
                        error_signature=signature,
                        out_of_scope_files=unsafe_scope,
                    ),
                    feedback=message,
                )
            state.latest_snapshot = asdict(latest.snapshot)
            state.current_error = latest.feedback or None
            state.error_signature = latest.snapshot.error_signature

            if latest.passed:
                state.status = TaskStatus.AWAITING_APPROVAL
                state.next_action = "codex_final_review"
                state.no_progress_attempts = 0
                self.state_store.save(state)
                return ControlledFlowResult(
                    task.task_id,
                    state.status,
                    attempt,
                    state.next_action,
                    False,
                    latest,
                )

            decision = self.engine.evaluate(
                previous=previous,
                current=latest.snapshot,
                local_attempt=attempt,
                no_progress_attempts=state.no_progress_attempts,
            )
            if decision.improved:
                state.no_progress_attempts = 0
            else:
                state.no_progress_attempts += 1

            if decision.action is ProgressAction.ESCALATE_CODEX:
                package = build_codex_escalation_package(
                    state=state,
                    failed_tests=list(latest.failed_tests),
                    relevant_diff=json.dumps(proposal, ensure_ascii=True, sort_keys=True),
                    progress_metrics=latest.snapshot,
                    technical_question=(
                        "Diagnosticar a falha e indicar uma correccao delimitada para a sandbox."
                    ),
                )
                package["automatic_call"] = False
                package["reasons"] = list(decision.reasons)
                self.state_store.save_escalation(task.task_id, package)
                state.status = TaskStatus.CODEX_REVIEW
                state.next_action = "await_manual_codex_review"
                state.escalation_history.append(
                    {"attempt": attempt, "reasons": list(decision.reasons)}
                )
                self.state_store.save(state)
                return ControlledFlowResult(
                    task.task_id,
                    state.status,
                    attempt,
                    state.next_action,
                    True,
                    latest,
                )

            state.status = TaskStatus.LOCAL_RETRY
            state.next_action = "request_local_correction"
            self.state_store.save(state)
            previous = latest.snapshot
            feedback = latest.feedback

        state.status = TaskStatus.FAILED_SAFE
        state.next_action = "manual_review"
        self.state_store.save(state)
        return ControlledFlowResult(
            task.task_id,
            state.status,
            state.attempts,
            state.next_action,
            False,
            latest,
        )


def parse_proposal_response(response: str) -> dict[str, str]:
    """Aceita apenas JSON com um mapa `files` de caminhos para conteudo."""
    text = response.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    decoded = json.loads(text)
    if not isinstance(decoded, dict) or set(decoded) != {"files"}:
        raise ValueError("proposta deve conter apenas a chave files")
    files = decoded["files"]
    if not isinstance(files, dict) or not files:
        raise ValueError("files deve ser um mapa nao vazio")
    if not all(isinstance(path, str) and isinstance(content, str) for path, content in files.items()):
        raise ValueError("caminhos e conteudos devem ser texto")
    return dict(files)


def apply_sandbox_proposal(
    *,
    workspace: Path,
    proposal: Mapping[str, str],
    allowed_paths: tuple[str, ...],
) -> tuple[str, ...]:
    if not proposal:
        raise ValueError("proposta vazia")
    workspace = workspace.resolve()
    changed: list[str] = []
    for relative, content in sorted(proposal.items()):
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise ValueError(f"caminho inseguro: {relative}")
        normalized = pure.as_posix()
        if not any(normalized == prefix.rstrip("/") or normalized.startswith(prefix.rstrip("/") + "/") for prefix in allowed_paths):
            raise ValueError(f"ficheiro fora do ambito: {relative}")
        target = (workspace / Path(*pure.parts)).resolve()
        _assert_within(target, workspace)
        if target.exists() and target.is_symlink():
            raise ValueError(f"symlink nao permitido: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        changed.append(normalized)
    return tuple(changed)


def validate_python_sandbox(workspace: Path, changed_files: tuple[str, ...]) -> ValidationResult:
    """Executa somente pytest, Ruff e mypy na sandbox indicada."""
    commands = (
        ("python3", "-m", "pytest", "-q"),
        (str(Path.home() / ".local" / "bin" / "ruff"), "check", ".", "--no-cache"),
        ("python3", "-m", "mypy", "."),
    )
    outputs: list[str] = []
    codes: list[int] = []
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        codes.append(completed.returncode)
        outputs.append((completed.stdout + "\n" + completed.stderr).strip())

    pytest_output, ruff_output, mypy_output = outputs
    passed = _last_int(r"(\d+) passed", pytest_output)
    failed = _last_int(r"(\d+) failed", pytest_output)
    lint_errors = 0 if codes[1] == 0 else max(1, len(re.findall(r"^.+:\d+:\d+: [A-Z]\d+", ruff_output, re.MULTILINE)))
    type_errors = 0 if codes[2] == 0 else max(1, _last_int(r"Found (\d+) errors?", mypy_output))
    combined = "\n".join(output for output in outputs if output)
    signature = None if all(code == 0 for code in codes) else hashlib.sha256(combined.encode()).hexdigest()[:16]
    snapshot = ProgressSnapshot(
        tests_passed=passed,
        tests_failed=failed if codes[0] == 0 else max(1, failed),
        lint_errors=lint_errors,
        type_errors=type_errors,
        changed_files=changed_files,
        diff_lines=sum((workspace / path).read_text(encoding="utf-8").count("\n") + 1 for path in changed_files),
        error_signature=signature,
    )
    feedback = "" if all(code == 0 for code in codes) else combined[-4000:]
    failed_tests = tuple(sorted(set(re.findall(r"FAILED ([^ ]+)", pytest_output))))
    return ValidationResult(snapshot, failed_tests, feedback)


def _last_int(pattern: str, text: str) -> int:
    matches = re.findall(pattern, text)
    return int(matches[-1]) if matches else 0


def _assert_within(path: Path, root: Path) -> None:
    if path != root and root not in path.parents:
        raise ValueError("caminho fora da sandbox")


def _call_with_timeout(
    function: Callable[..., Any],
    arguments: tuple[Any, ...],
    timeout: float,
) -> Any:
    """Executa uma operacao limitada sem deixar o processo principal bloqueado."""
    results: Queue[tuple[bool, object]] = Queue(maxsize=1)

    def target() -> None:
        try:
            results.put((True, function(*arguments)))
        except Exception as exc:  # noqa: BLE001 - fronteira controlada do fornecedor
            results.put((False, exc))

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    try:
        succeeded, value = results.get(timeout=timeout)
    except Empty as exc:
        raise TimeoutError("operation_timeout") from exc
    if not succeeded:
        if isinstance(value, Exception):
            raise value
        raise RuntimeError("resultado de operacao invalido")
    return value
