# ODIN alive-demo delivery plan

## Objective

Run ODIN as a local, observable Forex research system. It must expose health,
data quality, errors and controls through one dashboard. It is not authorised
to send real orders. The first live-like milestone is real read-only data and
continuous observation; a demo broker is a later, explicitly approved phase.

## Operating model

- Single WSL distribution: `Ubuntu-ODIN`.
- Repository: `/home/odin/projects/odin` on `master`.
- Durable host storage: `D:\ODIN_LOCAL` for checkpoints, reports, test results,
  logs and cached market data.
- Runtime mode: `shadow`; `safe_to_trade`, `real_trading` and
  `execution_allowed` stay `false`.
- The dashboard is the operator cockpit. It is read-only; configuration changes
  are reviewed local-file changes, never HTTP actions.

## Delivery milestones

| Milestone | Deliverable | Evidence required to pass |
| --- | --- | --- |
| M0 Base | One WSL, reproducible smoke, local checkpoint | WSL list, smoke PASS, clean Git |
| M1 Cockpit | Dashboard health, logs, Hermes, alerts and runbook | API smoke and documented diagnosis flow |
| M2 Data | Read-only Forex history/live observation cache | source, timestamp, schema and quality gates recorded |
| M3 Shadow | Continuous observation with watchdog and daily report | restart/failure log, no execution flags changed |
| M4 Demo-ready | Demo guard, secret handling, limits and kill switch | guard rejects non-DEMO account and no order path is active |

Only one milestone is active at a time. A failed gate produces a dashboard
event and a repair task; it never enables execution as a workaround.

## Dashboard contract

The dashboard must answer without a terminal: is ODIN/Hermes healthy; is data
fresh and quality-gated; what failed recently; are execution/account guards
blocked; and are CPU/GPU, disk, SQLite and Ollama within limits.

The cockpit views are: Overview, Runtime & Hermes, Data Quality, Events/Errors,
Research Reports, Resource Guard, and Configuration Summary. Each labels mock,
read-only and demo states clearly. No view may display real-trading-ready while
a safety flag is false.

## Secrets and provider configuration

Copy `.env.example` to `.env` only on the local WSL filesystem. `.env` is
ignored by Git and never belongs in reports, logs or the `D:` archive.

- News/data providers: add only the key requested by the selected read-only
  adapter, for example `ODIN_NEWS_API_KEY=`.
- MT5 demo: use `ODIN_MT5_LOGIN`, `ODIN_MT5_PASSWORD` and
  `ODIN_MT5_SERVER`; never put values in YAML, Python, Git or dashboard input.
- `ODIN_MT5_ACCOUNT_MODE=demo` is required by the future adapter. Missing,
  unknown or `real` modes fail closed.

## Daily operation and diagnosis

1. Start with `scripts/validate_wsl.sh` or the bounded smoke command.
2. Start the dashboard locally with `python3 -m odin.cli dashboard`.
3. Review `/operations/overview`, `/logs/tail`, `/runtime/smoke` and
   `/hermes/runtime`.
4. Save daily reports and validation output under `D:\ODIN_LOCAL\reports` and
   `D:\ODIN_LOCAL\test-results`.
5. Stop on CPU/GPU >=80 C, CUDA error, OOM, stale/invalid data, failed safety
   flags or unavailable provider. Record the event before repair.

## Explicit non-goals until approved

- Real trading, real account credentials and real order submission.
- Automatic code application, push, merge or unattended daemon operation.
- Financial recommendations presented as advice or profitability guarantees.

## Definition of done: ready for supervised demo

ODIN is ready for a supervised demo only when all of the following are true:

1. One `Ubuntu-ODIN` distribution, a clean local `master`, a verified backup
   and reproducible smoke/validation evidence exist.
2. The dashboard is usable locally and shows runtime, Hermes, safety flags,
   data freshness/quality, recent errors, resources and configuration summary.
3. Logs, SQLite state, daily reports and test artefacts persist under
   `D:\ODIN_LOCAL`, with a documented diagnosis and recovery procedure.
4. A documented Forex read-only source has bounded timeouts, local cache,
   provenance, freshness/gap validation and failure events. No data failure can
   enable a decision or execution path.
5. Shadow observation has completed its approved reliability window with
   restart/failure evidence and all safety flags continuously blocked.
6. The demo guard rejects missing, unknown and real account modes; secrets are
   absent from Git, logs, dashboard and reports; kill switch is tested.
7. Focused tests, full validation, Ruff, `git diff --check`, dashboard smoke
   and a final operator walkthrough pass.

At that point the automation stops adding backlog work and reports
`READY_FOR_SUPERVISED_DEMO`. Any demo login or order capability remains a
separate explicit operator authorization.
