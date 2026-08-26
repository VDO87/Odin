# ODIN DEMO EXECUTION RC1 — ACCEPTANCE REPORT

Current verdict: **ODIN DEMO EXECUTION RC1 — CANARY READY — HUMAN CONFIRMATION REQUIRED**

Reason: offline acceptance is green and live Stage 0 completed with fresh
market data, `ALLOW_DEMO`, `RECONCILED` and an accepted broker `order_check`.
The live result remains pre-submission: the CANARY has not been authorized or
executed and `broker_submission_called=false`.

## Baseline and checkpoints

- Preserved accepted baseline: `9f1df38`
- Preserved Shadow Intelligence RC: `477c2ce`
- Preserved supervision checkpoint: `ec18a3a`
- Branch: `feature/demo-live-soak-rc1`
- Policy authorization: `1d09774`
- Deterministic gate and Risk: `2715d7e`
- Adapter, ledger and reconciliation: `0c7b9ba`
- Financial observability: `07eddb3`
- Failure/recovery hardening: `5585171`
- Stage 0 launcher: `9303278`
- Stage 0 diagnostics: `8ff08ad`
- Scoped security sentinels: `090712a`
- Controlled CANARY pre-flight evidence: `3418d8b`
- Canonical `EURUSD` to OANDA `EURUSD.pro` mapping: `b45401e`
- MT5 filling flags to order policy correction: `b37c017`
- Automatic merge: not performed.

## Definition of Done matrix

| Criterion | Status | Evidence |
|---|---|---|
| Dedicated branch and recoverable baseline | PASS | Branch created from accepted supervision checkpoint; no merge |
| DEMO account gate | PASS | Exact terminal process, broker, server, configured login and `ACCOUNT_TRADE_MODE_DEMO` required |
| REAL/UNKNOWN account hard block | PASS | Parametrized gate and live-adapter tests |
| Risk Engine mandatory | PASS | `ALLOW_DEMO/BLOCK/KILL`; conservative documented limits |
| Demo Execution Gate | PASS | DEMO-only dry-run and one-shot CANARY scopes; global flags remain false |
| `order_check` integration | PASS | Live `order_check` accepted with retcode `0` and comment `Done`; no submission |
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
| Live Stage 0 | PASS | `DRY_RUN_VALIDATED`; FRESH data, `ALLOW_DEMO`, `RECONCILED`, accepted `order_check` |
| First CANARY | WAITING | Separate proposal-specific human confirmation is required; no submission made |

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

The live Stage 0 at `2026-08-26T15:04:55Z` proved:

- account mode DEMO;
- broker `OANDA TMS Brokers S.A.`;
- server `OANDATMS-MT5`;
- correct running terminal executable;
- DEMO balance and equity EUR 50,000.00;
- zero broker/local reconciliation discrepancy;
- `terminal_trade_allowed=true` on the verified OANDATMS-MT5 DEMO terminal;
- canonical symbol `EURUSD`, broker symbol `EURUSD.pro`, tradable;
- normalized market-data age 7 seconds and FRESH;
- Risk status `ALLOW_DEMO` with estimated maximum loss EUR 0.86 at 0.01 lot;
- reconciliation `RECONCILED`;
- `order_check.retcode=0`, comment `Done`;
- raw Stage 0 report SHA-256
  `85ac8d9d5e2aeb779137dc3588ed01fb1865c51ecb6c4abb5498746d94ba012d`;
- no broker submission call.

The prior `filling_mode_error` was caused by treating the symbol's
`SYMBOL_FILLING_MODE` bitmask as if it were an `ORDER_FILLING_*` enum. The
adapter now maps the documented FOK/IOC flags explicitly, prefers FOK to avoid
partial CANARY fills and blocks unknown Market Execution modes. Focused proof:
95 tests passed, Ruff passed, mypy passed and `git diff --check` passed before
checkpoint `b37c017`.

## Mandatory human stop

Stage 0 is complete. Do not repeat it and do not call the isolated broker
submission boundary until a new explicit human confirmation is bound to one
CANARY proposal and the verified DEMO account fingerprint. Any expired proposal
must be replaced and revalidated; authorization cannot be reused.

Current state:

`ODIN DEMO EXECUTION RC1 — CANARY READY — HUMAN CONFIRMATION REQUIRED`

## Guardrails

```text
safe_to_trade=false
real_trading=false
execution_allowed=false
```

No DEMO order and no REAL order were executed during this RC1 acceptance run.
