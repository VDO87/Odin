# ODIN DEMO EXECUTION RC1 — ACCEPTANCE REPORT

Current verdict: **ODIN DEMO EXECUTION RC1 — CANARY LIFECYCLE COMPLETE AND RECONCILED**

Reason: explicit human confirmation authorized one DEMO CANARY. It filled at
0.01 lot, reconciled against broker truth and consumed the one-shot marker.
The position later closed at its SL. MT5 history, the DEMO Decision Ledger and
the Execution Ledger now reconcile append-only through final state `CLOSED`.
New broker actions remain disabled.

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
- Human-gated CANARY runner: `6d8eb5b`
- Final reconciliation persistence: `43a5367`
- Broker position identifier linkage: `3b2b8b3`
- Read-only post-CANARY monitor: `6ec4215`
- Factual monitor reporting: `77f0ed5`
- Broker-time/freshness separation and lifecycle auditor: `3665d13`
- Automatic merge: not performed.

## Definition of Done matrix

| Criterion | Status | Evidence |
|---|---|---|
| Dedicated branch and recoverable baseline | PASS | Branch created from accepted supervision checkpoint; no merge |
| DEMO account gate | PASS | Exact terminal process, broker, server, configured login and `ACCOUNT_TRADE_MODE_DEMO` required |
| REAL/UNKNOWN account hard block | PASS | Parametrized gate and live-adapter tests |
| Risk Engine mandatory | PASS | `ALLOW_DEMO/BLOCK/KILL`; conservative documented limits |
| Demo Execution Gate | PASS | DEMO-only dry-run and one-shot CANARY scopes; global flags remain false |
| `order_check` integration | PASS | Live Stage 0 and CANARY checks accepted before the single submission |
| Submission isolated | PASS | AST sentinel proves one isolated broker submission call in the authorized adapter |
| Human CANARY gate | PASS | Repo control is disarmed; short, proposal/account-bound authorization required |
| Idempotency | PASS | Atomic proposal reservation, one-shot CANARY marker and duplicate tests |
| Decision to Execution linkage | PASS | Dedicated hash-chained DEMO Decision Ledger links the human decision and proposal to the Execution Ledger; the historical gap is explicitly marked retrospective |
| MT5 reconciliation | PASS | Broker is source of truth; mismatch/orphan/side/volume/entry/SL/TP blocks |
| Restart/recovery | PASS | Disconnect, reconnect, response-lost, submitted order and open-position scenarios tested |
| SL/TP and sizing | PASS | Direction, distance, point/digits, volume min/max/step and fixed 0.01 tested |
| Financial dashboard | PASS | DEMO balance/equity/P&L/drawdown/margin, Risk, execution and position state |
| Daily Supervisor | PASS | Execution anomalies, reconciliation and Hermes-versus-reality claims integrated |
| Hermes financially read-only | PASS | Component sentinels and full suite |
| n8n financially read-only | PASS | Policy forbids financial authority; n8n not installed or added |
| Secret redaction | PASS | Redaction tests and sanitized MT5/ledger outputs |
| Live Stage 0 | PASS | `DRY_RUN_VALIDATED`; FRESH data, `ALLOW_DEMO`, `RECONCILED`, accepted `order_check` |
| First CANARY | PASS | Human-confirmed BUY 0.01 lot filled once, reconciled and linked to the ledger |
| Post-CANARY soak | PASS | 275 read-only cycles; stopped fail-closed when the broker position disappeared, then MT5 history proved and reconciled the SL closure |

## Automated acceptance evidence

Latest full suite, without exclusions, at checkpoint `2b48bd5`:

- collected: 768;
- passed: 768;
- failed: 0;
- skipped: 0;
- subtests: 42 passed;
- pytest duration: 538.58 seconds (`0:08:58`);
- wall duration: 540.11 seconds;
- file descriptor soft limit: 8192;
- maximum RSS: 258,244 KB.

Additional gates:

- focused DEMO execution and security matrix: 99 passed;
- post-CANARY monitor matrix: 70 passed;
- legacy and global financial sentinels: 64 passed;
- Stage 0 contract plus core execution regressions: 69 passed;
- Ruff: `ruff check .` passed;
- mypy directed scope: 10 RC1 source files passed with no issues;
- `git diff --check`: passed.

Current lifecycle/time-normalization scope at checkpoint `3665d13`: 128 tests
passed, Ruff passed, mypy passed on 7 source files and `git diff --check`
passed. No full-suite result is inferred from the focused run.

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

## Live CANARY result

The human-confirmed one-shot at `2026-08-28T09:14:46Z` produced:

- proposal `rc1-canary-55d3609121062f574b92`;
- decision `rc1-canary-human-confirmed`;
- canonical symbol `EURUSD`, broker symbol `EURUSD.pro`;
- BUY 0.01 lot;
- requested and executed price 1.16437; slippage 0 points;
- SL 1.16337; TP 1.16637;
- `TRADE_RETCODE_DONE` (`10009`), submission status `FILLED`;
- order/position id `151407246`, deal `105358964`;
- maximum loss estimate EUR 0.86;
- broker and Execution Ledger reconciliation `RECONCILED`;
- CANARY report SHA-256
  `74f891b5c7b7fa707e176855e58cee207f4e7a40836d13da7676dbd1ef115d18`;
- one-shot marker present; no retry or second submission path enabled.

The bounded read-only monitor completed 275 cycles over 17,261 seconds with
100% fresh-data cycles, zero exceptions and no new broker action. At
`2026-08-28T14:02:27Z` it observed zero positions and stopped fail-closed with
`reconciliation_mismatch`, because the local ledger still represented the
previously reconciled open position.

The lifecycle audit subsequently proved from MT5 broker history:

- entry deal `105358964`, order/position `151407246`, BUY 0.01 at 1.16437;
- entry time `2026-08-28T09:14:39Z` after CET/CEST normalization;
- exit deal `105378769`, order `151427905`, at 1.16335;
- exit time `2026-08-28T14:01:42Z` after CET/CEST normalization;
- close reason `SL`, with 2 points of exit slippage relative to 1.16337;
- realized P/L EUR -0.88; commission, swap and fee all EUR 0.00;
- no open position and no pending order;
- Execution Ledger state `CLOSED / RECONCILED`, hash chain valid;
- DEMO Decision Ledger state `OK`, with the recovered historical decision
  explicitly labelled retrospective;
- lifecycle report SHA-256
  `c63abe4958a3a908386e17528199d76924a7edd3f195202e66f785b715b53103`.

The stale weekend tick was also normalized correctly: raw broker wall-clock
epoch represented `2026-08-28T22:58:59`, the audited summer profile applied
`+7200`, and the normalized event time is `2026-08-28T20:58:59Z`. Freshness is
`STALE` with only `stale_data` / `stale_data_threshold_exceeded`; the time
profile remains `VALID`, confidence `HIGH`.

## Mandatory post-CANARY stop

Do not open a second position. The first CANARY lifecycle is complete, but this
audit grants no SMALL BATCH or new execution authority. The terminal currently
reports `terminal_trade_allowed=false`; ODIN did not alter it.

Current state:

`ODIN DEMO EXECUTION RC1 — CANARY LIFECYCLE COMPLETE_AND_RECONCILED`

## Guardrails

```text
safe_to_trade=false
real_trading=false
execution_allowed=false
```

Exactly one DEMO order and zero REAL orders were executed during this RC1 run.
The global flags remain false and no new DEMO execution is enabled.
