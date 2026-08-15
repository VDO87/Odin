---
name: odin-blocker-triage
description: Diagnose an ODIN build, test, runtime, dependency, documentation, permission, or environment blocker before any correction. Use whenever progress is stopped, an error recurs, an instruction is ambiguous, or a command gives conflicting evidence.
---

# ODIN Blocker Triage

1. Capture the exact symptom, command, exit status, relevant versions, and minimal logs.
2. Classify it: code defect, test defect, configuration, dependency, environment, missing evidence, or external decision.
3. Form a falsifiable hypothesis and run the smallest safe discriminating check.
4. Correct only after the cause is supported; validate the correction with focused evidence.
5. Escalate with concise evidence if credentials, licensing, guardrails, destructive action, data-loss risk, or a human decision is required.

Never suppress an error, loosen a guardrail, delete tests, or retry the same action without new information.
