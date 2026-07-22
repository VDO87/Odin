# ODIN delivery backlog

This is the ordered delivery queue for the daily automation. A completed item
is not repeated; the next unchecked item becomes the next concrete task.

## M1 — Operational cockpit

- [ ] Add one dashboard overview payload that includes runtime, Hermes, data,
  safety flags, resource guardian and recent error count.
- [ ] Serve a local HTML cockpit shell with navigation and no write actions.
- [ ] Add dashboard panels for safety flags, component health and active alerts.
- [ ] Add an events/errors panel with severity, timestamp, component and safe
  next action.
- [ ] Add resource panel for disk, CPU/GPU probe status and Ollama state.
- [ ] Add configuration summary that redacts all secrets and explains mode.
- [ ] Add dashboard API and browser smoke coverage.
- [ ] Persist a daily operational report under `D:\ODIN_LOCAL\reports`.
- [ ] Document startup, shutdown, diagnosis and recovery workflows.

## M2 — Read-only Forex data

- [ ] Define the canonical candle/history CSV schema and provenance contract.
- [ ] Add a local CSV importer with strict validation and fail-closed errors.
- [ ] Add a cache layout under `D:\ODIN_LOCAL\artifacts\market-data`.
- [ ] Add data freshness, duplicate, gap and timestamp-quality gates.
- [ ] Add dashboard source/freshness/provenance panels.
- [ ] Select a documented public Forex data/news provider with the operator.
- [ ] Add a bounded read-only provider adapter with cache and timeout.
- [ ] Record provider failures as dashboard events; never generate a signal.

## M3 — Shadow operation

- [ ] Define a shadow-cycle state machine and idempotent run record.
- [ ] Add bounded single-cycle CLI with watchdog-compatible exit status.
- [ ] Add failure/restart and stale-data simulations.
- [ ] Add daily comparison report: source freshness, observations and failures.
- [ ] Add explicit operator procedure for approving a persistent local process.

## M4 — Demo-ready guardrails

- [ ] Define a demo account configuration contract with redacted fields.
- [ ] Add guard that rejects missing, unknown and real account modes.
- [ ] Add a kill-switch contract and dashboard status.
- [ ] Add secret-loading tests proving `.env` values cannot reach logs/events.
- [ ] Add MT5 terminal detection only; no login and no order path.
- [ ] Obtain operator approval before any demo login or order capability.

## Completion rule

For every item: implementation, focused test, documentation update, `git diff
--check`, local Git checkpoint, and one line in the daily report. Items that
need an operator decision are marked blocked and the automation continues with
the next independent item.
