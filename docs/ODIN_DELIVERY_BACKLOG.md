# ODIN delivery backlog

This is the ordered delivery queue for the daily automation. A completed item
is not repeated; the next unchecked item becomes the next concrete task.

## M1 — Operational cockpit

- [x] Add one dashboard overview payload that includes runtime, Hermes, data,
  safety flags, resource guardian and recent error count.
- [x] Serve a local HTML cockpit shell with navigation and no write actions.
- [x] Add dashboard panels for safety flags, component health and active alerts.
- [x] Add an events/errors panel with severity, timestamp, component and safe
  next action.
- [x] Add resource panel for disk, CPU/GPU probe status and Ollama state.
- [x] Add configuration summary that redacts all secrets and explains mode.
- [x] Add dashboard API and local launcher smoke coverage.
- [x] Persist a daily operational report under `D:\ODIN_LOCAL\reports`.
- [x] Document startup, shutdown, diagnosis and recovery workflows.

## M2 — Read-only Forex data

- [x] Define the canonical candle/history CSV schema and provenance contract.
- [x] Add a local CSV importer with strict validation and fail-closed errors.
- [x] Add a cache layout under `D:\ODIN_LOCAL\artifacts\market-data`.
- [x] Add data freshness, duplicate, gap and timestamp-quality gates.
- [x] Add dashboard source/freshness/provenance panels.
- [x] Select a documented public Forex provider: ECB EXR, observation-only.
- [x] Add a bounded read-only provider adapter with cache and timeout.
- [x] Record provider failures as dashboard events; never generate a signal.

## M3 — Shadow operation

- [x] Define a shadow-cycle state machine and idempotent run record.
- [x] Add bounded single-cycle CLI with watchdog-compatible exit status.
- [x] Add failure/restart and stale-data simulations.
- [x] Add daily comparison report: source freshness, observations and failures.
- [x] Add explicit operator procedure for approving a persistent local process.

## M4 — Demo-ready guardrails

- [x] Define a demo account configuration contract with redacted fields.
- [x] Add guard that rejects missing, unknown and real account modes.
- [x] Add a kill-switch contract and dashboard status.
- [x] Add secret-loading tests proving `.env` values cannot reach logs/events.
- [x] Add MT5 terminal detection and a bounded, read-only DEMO collector; no order path.
- [x] Obtain operator approval before the one authorised DEMO read-only login check.

## Completion rule

For every item: implementation, focused test, documentation update, `git diff
--check`, local Git checkpoint, and one line in the daily report. Items that
need an operator decision are marked blocked and the automation continues with
the next independent item.

## Current DEMO gate

The local supervised DEMO observation path is ready: TradeDesk and cockpit are
on localhost, MT5 DEMO state is integrity-checked and stale after 15 minutes,
public ECB evidence is cached, and the manual refresh persists audits and
reports on `D:\ODIN_LOCAL`. Shadow cycles, persistent processes, strategy
decisions and every form of order capability remain unchecked and blocked.
