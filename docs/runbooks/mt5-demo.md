# MT5 demo runbook

Preconditions: terminal detected; no real-account warning; verified DEMO secrets only in ignored local .env; guard/kill switch/restart/reconciliation/redaction/idempotency tests pass; explicit human login authorization exists.

Current phase: ODIN DEMO EXECUTION RC1 infrastructure and dry-run. Existing
credentials and account selection are not changed. Account identity must be
proved from terminal evidence; missing/unknown/REAL/mismatch stop before any
execution call. Provider/global timeouts, watchdog, telemetry, idempotency and
reconciliation remain bounded.

`order_check` may be used during controlled dry-run after the deterministic
gate. The first `order_send` remains prohibited until all offline tests pass, a
PRE-FLIGHT report is reviewed and the operator gives a specific one-shot CANARY
confirmation. That confirmation authorizes one DEMO proposal only and never
authorizes REAL, retries without reconciliation, or another account.
