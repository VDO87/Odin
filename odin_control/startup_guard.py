from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class HealthRunner(Protocol):
    def run(self) -> dict[str, object]: ...


class Reconciler(Protocol):
    def reconcile(self) -> dict[str, object]: ...


@dataclass(slots=True)
class StartupGuardResult:
    health_ok: bool
    reconciliation_ok: bool
    blocked_reason: str | None = None


class StartupGuard:
    def __init__(self, health_runner: HealthRunner, reconciler: Reconciler) -> None:
        self.health_runner = health_runner
        self.reconciler = reconciler

    def validate(self) -> StartupGuardResult:
        health = self.health_runner.run()
        if health.get("status") in {"CRITICAL", "BLOCKED"}:
            return StartupGuardResult(False, False, "healthcheck_failed")

        rec = self.reconciler.reconcile()
        if not bool(rec.get("ok", False)):
            return StartupGuardResult(True, False, "position_reconciliation_failed")
        return StartupGuardResult(True, True, None)
