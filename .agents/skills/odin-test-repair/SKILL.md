---
name: odin-test-repair
description: Repair an ODIN test or validation failure while preserving test integrity and project safety. Use when a focused test, lint, type check, integration check, or regression test fails during an active ODIN objective.
---

# ODIN Test Repair

1. Reproduce the narrowest failing check and preserve its output.
2. Read the test, the exercised code, and the relevant contract or documentation; distinguish a product defect from an invalid test expectation.
3. Fix the supported root cause with the smallest reversible change. Do not remove, skip, weaken, or rewrite a test merely to make it pass.
4. Run the original focused check, then the smallest relevant regression set.
5. Record the commands and results; create a checkpoint only after the tree is stable and validation passes.

For flaky, resource, timeout, or leak symptoms, use `odin-blocker-triage` and `odin-bounded-loop`; do not increase limits indefinitely to conceal the defect.
