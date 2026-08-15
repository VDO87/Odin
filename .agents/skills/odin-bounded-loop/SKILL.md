---
name: odin-bounded-loop
description: Run a bounded, evidence-led ODIN diagnosis and correction loop. Use for debugging, failing tests, runtime incidents, recurring commands, leak symptoms, or any repair cycle where repeated attempts could hide lack of progress.
---

# ODIN Bounded Loop

Execute in order: **observar → recolher evidência → formular hipótese → testar → corrigir → verificar → medir progresso**.

- Run a command at most twice without new evidence.
- Consider at most three similar hypotheses; then reformulate the diagnosis from the accumulated evidence.
- Never repeat a failed attempt without new information.
- Preserve functional checkpoints; prefer small, reversible corrections.
- Measure progress with a concrete signal: a narrower failure, a passing focused check, reduced reproduction, or confirmed root cause.
- Stop and escalate when progress stalls, the remaining action is unsafe, or an AGENTS.md stop condition applies.

Do not conceal leaks or instability by indefinitely raising timeouts, retries, workers, memory, file-descriptor, or other limits.
