# ODIN Supervision and Controlled Evolution Loop

**Status:** manual, local-first supervision loop. It is not an execution
system, a scheduler, or an authorization to modify the running system.

```text
safe_to_trade=false
real_trading=false
execution_allowed=false
```

## Authority boundary

```text
MT5 DEMO read-only / historical data / Decision Ledger
                     |
                     v
TradeDesk + cockpit + Shadow Intelligence + Hermes evidence
                     |
                     v
Daily Supervisor report ----> human review ----> bounded Codex handoff
                     |
                     v
Weekly Evolution Gate -----> at most one proposed initiative
```

Risk/Treasury, deterministic gates and the kill switch remain authoritative.
Hermes and any future n8n workflow can observe, summarize and propose work;
they cannot alter safety, risk, sizing, the kill switch, broker reconciliation
or invoke an order API.

## Daily Supervisor

The intended review window is **08:00 Europe/Lisbon**, covering the preceding
24 hours. It is deliberately **manual only**: no cron entry, service, Task
Scheduler task, daemon or automatic code change is created by this feature.

Run it from WSL:

```sh
cd /home/odin/projects/odin
python3 -m odin.cli daily-supervisor --output-dir /mnt/d/ODIN_LOCAL/reports
```

The report is written as JSON and Markdown below
`D:\ODIN_LOCAL\reports` and records only local evidence from:

- MT5 DEMO read-only observation and audit state;
- TradeDesk/cockpit localhost reachability (the command never starts them);
- replay or DEMO-observation metrics, explicitly labelled as non-financial;
- Shadow Intelligence, accepted historical-data status and freshness;
- Hermes read-only summary and structured claim scorecard;
- operational alerts and resource evidence.

It selects at most one suggestion: `SECURITY_RECONCILIATION`, `DATA_QUALITY`,
`DASHBOARD_OBSERVABILITY`, or `NO_CHANGE`. A suggestion is not a task launch
and not a permission for code modification.

## Hermes versus reality

Hermes is assessed only against compact structured claims, never against its
free-form prose. The initially supported claim kinds are `mt5_connected`,
`historical_data_status`, and `execution_allowed`. Every claim is classified
as one of:

| Result | Meaning |
|---|---|
| `CONFIRMED` | Exact observed value matches the claim. |
| `PARTIAL` | Equivalent accepted status with an integration-level naming difference. |
| `NOT_CONFIRMED` | Evidence is absent or the claim kind has no defined verifier. |
| `CONTRADICTED` | The available observation disagrees with the claim. |

Root-cause labels are bounded to `PROMPT`, `WEAK_SOURCE`, `STALE_SOURCE`,
`MISSING_CONTEXT`, `HALLUCINATION`, `INTEGRATION`, `MODEL_LIMITATION`, and
`UNKNOWN`. No label is inferred when evidence is unavailable. Credentials and
sensitive-key claim fields are redacted before report persistence.

## Weekly Evolution Gate

The intended window is **Saturday 08:00 Europe/Lisbon**, using the last seven
days of Daily Supervisor reports. It aggregates evidence and proposes at most
one initiative for human review. It never runs that initiative.

```sh
cd /home/odin/projects/odin
python3 -m odin.cli weekly-evolution-gate \
  --reports-dir /mnt/d/ODIN_LOCAL/reports \
  --output-dir /mnt/d/ODIN_LOCAL/reports
```

With no daily evidence, the gate is explicitly `BLOCKED` with `NO_EVIDENCE`;
it does not invent a weekly improvement. With healthy evidence, the result is
`NO_CHANGE_REQUIRED`.

## Bounded Codex handoff

When a daily suggestion exists, the report contains an inert handoff template:

```text
objective
evidence
scope
baseline
guardrails
tests
definition_of_done
stop_conditions
```

The operating limits are: at most two executions of the same command without
new evidence, at most three similar hypotheses, and immediate human approval
for dependencies, persistent processes, credentials or any trading-related
operation. A normal handoff can diagnose and perform the smallest reversible
repair only after the user authorizes the goal.

## n8n and Notion evaluation

No n8n, Docker runtime, n8n state directory or ODIN/n8n scheduled task was
present in the 2026-08-22 audit. The existing supervisor, Decision Ledger,
reports and manual CLI already meet the initial local evidence need, so n8n is
not installed or configured now.

If a future self-hosted n8n proposal is useful, it must be presented for
explicit approval before installation. The proposal must specify its purpose,
components, port exposure, persistence location, local security boundary,
rollback and exact install plan. n8n Cloud is out of scope. It may only
trigger report generation and human notifications; it may never hold financial
authority.

Notion is likewise not connected or updated by this loop. A future factual
update may publish a report summary only after an explicit human authorization
and must never copy credentials, logs containing secrets, or financial controls.

## Report contract and safe stop

Every report contains:

- UTC generation time and manual schedule intent;
- the three false guardrails;
- data sources, observed/expected period and missing-evidence state;
- Hermes scorecard and root-cause counts;
- priority/evolution result plus an explicit `automatic_change_started=false`;
- JSON plus a human-readable Markdown rendering.

There is no process to stop after either command: both commands exit after
writing evidence. If a separately authorized bounded dashboard process is
running, use its documented launcher stop procedure; this loop neither starts
nor stops it.
