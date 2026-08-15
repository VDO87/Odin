# ODIN DEMO BASELINE — Acceptance Report

**Date:** 2026-08-15  
**Branch:** `audit/p0-safety-and-docs`  
**Implementation checkpoint:** `f5f58e3`  
**P0 dataset checkpoint:** `690f6b9`

## Decision

**ODIN DEMO BASELINE — READY FOR SUPERVISED TESTING**

This is a local, supervised, observation/replay baseline only. It does not
authorise DEMO or real trading.

```text
safe_to_trade=false
real_trading=false
execution_allowed=false
```

## Validation evidence

| Check | Result |
|---|---|
| Full test suite | `623 passed`, `42 subtests passed`, `0 failed`, `0 skipped` |
| Full-suite duration | `453.22s` (7m33s) |
| File-descriptor limit | `8192` during full suite |
| MT5 guard sentinels | `19 passed` (`test_a5_*`, `test_a6_*`, `test_a7_*`) |
| P0 specific suite | `20 passed` |
| TradeDesk/cockpit/replay/redaction/read-only suite | `20 passed` |
| Ruff | `ruff check .` passed |
| Mypy (changed P0 adapter scope) | passed |
| Git whitespace validation | `git diff --check` passed |

## Dataset and provenance

- Provider: `OANDA TMS Brokers S.A.` via `MetaTrader 5`, server `OANDATMS-MT5`.
- Symbol/timeframe: `EURUSD`, RAW BID M1 UTC; deterministic complete-window M1→M15.
- Requested period: `[2026-07-01T00:00:00Z, 2026-08-01T00:00:00Z)`.
- RAW: 32,888 bars; SHA-256
  `3484f28eab61c60e78cd0f4c1e7ca4d9deedbb4e36d2e681b94858c58bb0f35a`.
- Quality: 54 gaps — 4 `EXPECTED_GAP`, 50 `NO_TICK_GAP`, 0
  `SUSPICIOUS_GAP`; active coverage `99.371525%`; no synthetic candles or
  forward-fill.
- Derived M15 SHA-256:
  `50e422310881add19674b390f06497070a61b2b1bc6470f77de57a9bca96c217`.
- Both RAW and M15 validated artifacts exist in `D:\ODIN_LOCAL\artifacts\market-data`.
- License/provenance are explicit and non-invented:
  `license_id=NOT_EXPLICITLY_STATED`, local internal validation/replay only,
  no redistribution rights inferred.

## Operational walkthrough

`docs/OPERATOR_WALKTHROUGH.md` was executed using the local watchdog launcher.

- Both Windows shortcuts exist, as do the TradeDesk launcher and controlled
  refresh launcher.
- TradeDesk (`/`), cockpit (`/cockpit`), canonical-history, replay and Hermes
  endpoints returned HTTP 200. The aggregated overview returned HTTP 200 in
  9.63 s.
- Controlled refresh completed with GPU at 42°C; MT5 DEMO was
  `CONNECTED_DEMO_READ_ONLY`, with zero positions and no execution.
- ECB public data was refreshed with source URL/provenance persisted.
- Shadow cycle was `OBSERVED_NO_DECISION`; replay remains visibly separate.
- Hermes was `LOCAL_ONLY`, read-only, and Ollama available.
- Operational report was written locally; kill-switch status is validated as a
  non-execution control and remains not engaged for the read-only observation.

## Definition of Done

All Definition-of-Done entries in `docs/ODIN_ESTADO_CANONICO_E_PLANO.md` have
evidence above: complete suite, validated P0 data and artifact persistence,
fail-closed import, redaction, TradeDesk/cockpit/shortcuts/launcher, fresh
MT5 DEMO read-only observation and reconciliation, ECB provenance, separate
replay, local Hermes without execution, kill-switch controls, guardrails,
walkthrough, clean diff check and this report.

## Residual constraints

- No autonomous daemon/service was created.
- No order path was called; no `order_send` capability is permitted.
- The baseline must remain local and supervised. Shadow Intelligence and new
  integrations are deliberately out of scope.

## Start and stop

Use `ODIN TradeDesk (Demo)` for the local dashboard and
`ODIN Refresh DEMO Observations` only for the bounded manual refresh. To stop,
close the local dashboard components; do not create a persistent process or
weaken any guardrail.
