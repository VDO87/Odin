# ODIN DEMO EXECUTION RC1 — ACCEPTANCE REPORT

Current verdict: **ODIN DEMO EXECUTION RC1 — WAITING FOR MARKET SESSION**

Reason: the full offline acceptance is green and the controlled DEMO scenario
reaches `CANARY READY — HUMAN CONFIRMATION REQUIRED` without broker submission.
The live Stage 0 remains paused on two external prerequisites: manual terminal
Algo/Auto Trading permission and a valid open EURUSD market session. The CANARY
has not been authorized or executed.

## Baseline and checkpoints

- Preserved accepted baseline: `9f1df38`
- Preserved Shadow Intelligence RC: `477c2ce`
- Preserved supervision checkpoint: `ec18a3a`
- Branch: `feature/demo-execution-rc1`
- Policy authorization: `1d09774`
- Deterministic gate and Risk: `2715d7e`
- Adapter, ledger and reconciliation: `0c7b9ba`
- Financial observability: `07eddb3`
- Failure/recovery hardening: `5585171`
- Stage 0 launcher: `9303278`
- Stage 0 diagnostics: `8ff08ad`
- Scoped security sentinels: `090712a`
- Controlled CANARY pre-flight evidence: `3418d8b`
- Automatic merge: not performed.

## Definition of Done matrix

| Criterion | Status | Evidence |
|---|---|---|
| Dedicated branch and recoverable baseline | PASS | Branch created from accepted supervision checkpoint; no merge |
| DEMO account gate | PASS | Exact terminal process, broker, server, configured login and `ACCOUNT_TRADE_MODE_DEMO` required |
| REAL/UNKNOWN account hard block | PASS | Parametrized gate and live-adapter tests |
| Risk Engine mandatory | PASS | `ALLOW_DEMO/BLOCK/KILL`; conservative documented limits |
| Demo Execution Gate | PASS | DEMO-only dry-run and one-shot CANARY scopes; global flags remain false |
| `order_check` integration | PARTIAL | Offline FakeMT5 path green; live check blocked before call by closed market |
| Submission isolated | PASS | AST sentinel proves one isolated broker submission call in the authorized adapter |
| Human CANARY gate | PASS | Repo control is disarmed; short, proposal/account-bound authorization required |
| Idempotency | PASS | Atomic proposal reservation, one-shot CANARY marker and duplicate tests |
| Decision to Execution linkage | PASS | `decision_id`, `proposal_id`, hashes and strategy version in hash-chained ledger |
| MT5 reconciliation | PASS | Broker is source of truth; mismatch/orphan/side/volume/entry/SL/TP blocks |
| Restart/recovery | PASS | Disconnect, reconnect, response-lost, submitted order and open-position scenarios tested |
| SL/TP and sizing | PASS | Direction, distance, point/digits, volume min/max/step and fixed 0.01 tested |
| Financial dashboard | PASS | DEMO balance/equity/P&L/drawdown/margin, Risk, execution and position state |
| Daily Supervisor | PASS | Execution anomalies, reconciliation and Hermes-versus-reality claims integrated |
| Hermes financially read-only | PASS | Component sentinels and full suite |
| n8n financially read-only | PASS | Policy forbids financial authority; n8n not installed or added |
| Secret redaction | PASS | Redaction tests and sanitized MT5/ledger outputs |
| Live Stage 0 | WAITING | External terminal permission and valid EURUSD market session are pending |
| First CANARY | NOT STARTED | Separate human confirmation required after green Stage 0 |

## Automated acceptance evidence

Full suite, without exclusions:

- collected: 711;
- passed: 711;
- failed: 0;
- skipped: 0;
- subtests: not separately reported by the installed pytest plugin set; any
  `unittest.subTest` activity is included in the 711 collected items;
- pytest duration: 653.17 seconds (`0:10:53`);
- wall duration: `0:10:55.07`;
- file descriptor soft limit: 8192;
- maximum RSS: 249,364 KB.

Additional gates:

- focused DEMO execution matrix: 72 passed;
- legacy and global financial sentinels: 64 passed;
- Stage 0 contract plus core execution regressions: 69 passed;
- Ruff: `ruff check .` passed;
- mypy directed scope: 9 RC1 source files passed with no issues;
- `git diff --check`: passed.

## Live Stage 0 result

The live probe proved:

- account mode DEMO;
- broker `OANDA TMS Brokers S.A.`;
- server `OANDATMS-MT5`;
- correct running terminal executable;
- DEMO balance and equity EUR 50,000.00;
- zero broker/local reconciliation discrepancy;
- estimated maximum loss EUR 0.87 at 0.01 lot;
- no broker submission call.

It rejected the proposal before `order_check` because the last tick was stale,
the closing spread exceeded the RC1 limit and the terminal-level trading
permission was false. These are separate gates: market reopening can restore
symbol mode, freshness and spread, but ODIN will still require the external
terminal permission to be explicitly true. This is the required fail-closed
result, but it does not satisfy the Stage 0 acceptance criterion.

## External stop condition

`MARKET_SESSION_REQUIRED` is accepted as the current external stop condition.
No further dry-run or retry is permitted while either prerequisite is missing.

### A. MT5 terminal

- The operator manually authorizes Algo/Auto Trading in the verified DEMO
  terminal.
- `terminal_trade_allowed=true` must be observed.
- ODIN does not change this terminal setting automatically.

### B. EURUSD

- market open;
- `symbol_trade_mode` compatible with trading;
- ticks FRESH;
- spread within the RC1 limit.

## Remaining acceptance action

Only after both external prerequisites are satisfied, run exactly once:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin\scripts\windows\Invoke-ODIN-MT5-Demo-DryRun.ps1"
```

If Stage 0 becomes green, update both reports and stop at:

`ODIN DEMO EXECUTION RC1 — CANARY READY — HUMAN CONFIRMATION REQUIRED`

Do not call the broker submission boundary until a new explicit human
confirmation is tied to that exact proposal and DEMO account fingerprint.
The expected pre-confirmation evidence remains
`broker_submission_called=false`.

## Guardrails

```text
safe_to_trade=false
real_trading=false
execution_allowed=false
```

No DEMO order and no REAL order were executed during this RC1 acceptance run.
