# ODIN DEMO EXECUTION RC1 — ACCEPTANCE REPORT

Current verdict: **ODIN DEMO EXECUTION RC1 — NOT READY**

Reason: the full offline acceptance is green, but the required live Stage 0
could not reach `order_check` while the Forex market was closed. The system
correctly blocked on terminal trade state, stale data and excessive closing
spread. The CANARY has not been authorized or executed.

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
| Live Stage 0 | BLOCKED | Market closed: stale tick, excessive spread and terminal trading unavailable |
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
the closing spread exceeded the RC1 limit and the terminal reported trading not
allowed during the closed session. This is the required fail-closed result, but
it does not satisfy the Stage 0 acceptance criterion.

## Remaining acceptance action

Repeat the exact command in `docs/ODIN_DEMO_CANARY_PREFLIGHT.md` once EURUSD is
open and producing fresh ticks. If Stage 0 becomes green, update both reports,
run the focused acceptance gates, and stop at:

`ODIN DEMO EXECUTION RC1 — CANARY READY — HUMAN CONFIRMATION REQUIRED`

Do not call the broker submission boundary until a new explicit human
confirmation is tied to that exact proposal and DEMO account fingerprint.

## Guardrails

```text
safe_to_trade=false
real_trading=false
execution_allowed=false
```

No DEMO order and no REAL order were executed during this RC1 acceptance run.
