---
name: odin-objective-runner
description: Coordinate a bounded ODIN engineering objective from evidence to validated completion. Use for any non-trivial ODIN implementation, repair, refactor, baseline task, or documentation change that has an active objective and must remain safe, scoped, reproducible, and fail-closed.
---

# ODIN Objective Runner

1. Read `AGENTS.md`, the canonical state/plan document, and task-relevant docs before significant work.
2. State one active objective and its Definition of Done; do not widen scope.
3. Use `odin-data-provenance` when inputs, fixtures, reports, or claims require origin/integrity checks.
4. Use `odin-blocker-triage` for failures, ambiguity, missing dependencies, or environment blockers.
5. Use `odin-test-repair` for a failing validation caused by the active objective.
6. Apply `odin-bounded-loop` to every diagnosis-and-correction cycle.
7. Finish only when the Definition of Done and proportional validation are satisfied, then create a Git checkpoint after confirming the stable diff.
8. Stop and request human direction only for a genuine external blocker or an AGENTS.md stop condition. Report evidence, impact, and the smallest decision needed.

Do not operate financial systems, weaken guardrails, create trading autonomy, or convert an incomplete baseline into a different objective.
