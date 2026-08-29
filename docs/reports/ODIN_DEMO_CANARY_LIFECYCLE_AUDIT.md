# ODIN DEMO CANARY — LIFECYCLE AUDIT

Audit time: `2026-08-29T10:32:10Z`  
Code checkpoint: `3665d13`  
Raw report: `D:\ODIN_LOCAL\reports\demo-execution\canary-lifecycle-audit.json`  
Raw report SHA-256: `c63abe4958a3a908386e17528199d76924a7edd3f195202e66f785b715b53103`

## Result

```text
CANARY POSITION: CLOSED
CANARY LIFECYCLE: COMPLETE_AND_RECONCILED
MT5 <-> LEDGER: RECONCILED
broker_submission_called=false (during this audit)
safe_to_trade=false
real_trading=false
execution_allowed=false
```

## Broker lifecycle evidence

| Field | Evidence |
|---|---|
| Broker / server | OANDA TMS Brokers S.A. / OANDATMS-MT5 |
| Terminal | `C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe` |
| Symbol | EURUSD / EURUSD.pro |
| Position | `151407246` |
| Entry | BUY 0.01 at 1.16437; deal `105358964`; order `151407246` |
| Entry time | raw `1787915679`; normalized `2026-08-28T09:14:39Z` |
| SL / TP | 1.16337 / 1.16637 |
| Entry spread | 0.00009 / approximately 9 points |
| Entry slippage | 0 points |
| Exit | SELL 0.01 at 1.16335; deal `105378769`; order `151427905` |
| Exit time | raw `1787932902`; normalized `2026-08-28T14:01:42Z` |
| Close reason | SL |
| Exit slippage from SL | approximately 2 points |
| Realized P/L | EUR -0.88 |
| Commission / swap / fee | EUR 0.00 / 0.00 / 0.00 |
| Open position / pending order | false / false |

The balance transition from EUR 50,000.00 to EUR 49,999.12 is fully explained
by the broker-recorded realized P/L. No assumption was used to attribute it.

## Time normalization

The former failure mixed two independent concepts. Candidate offsets were
accepted only when `raw_tick - host_now` was within a live-observation window.
That inferred timezone from freshness and converted a stale weekend tick into
`unexpected_broker_time_offset`.

The corrected flow is:

```text
raw broker wall-clock epoch
-> exact broker/server profile
-> CET/CEST rule evaluated at the event candidate
-> normalized UTC event time
-> host UTC minus normalized event time
-> freshness
```

Observed weekend evidence:

| Field | Value |
|---|---|
| Raw broker time | `1787957939` / represented as `2026-08-28T22:58:59` |
| Profile | `oanda_tms_mt5_cet_cest_v1` |
| Expected summer offset | `+7200` seconds |
| Normalized UTC | `2026-08-28T20:58:59Z` |
| Age at audit | `48791.47` seconds |
| Freshness | `STALE` |
| Reasons | `stale_data`, `stale_data_threshold_exceeded` |
| Time profile | `VALID`, confidence `HIGH` |

An independently supplied offset that disagrees with the event-date profile
still produces `unexpected_broker_time_offset`. Unknown broker/server, DST
ambiguity without offset evidence and future timestamps remain fail-closed.

## Ledgers and terminal state

- Execution Ledger: 11 records, latest `CLOSED / RECONCILED`, SHA-256
  `5d4b300558e6db928ebc5efbabe689b23b3b8441d19b174fc82538f1c17ccff3`.
- DEMO Decision Ledger: one retrospective recovery record, explicitly labelled
  as such, SHA-256
  `77aaec847589192169ab3f9311f9e0322a873e8f5347b090365094c3de96a817`.
- Both ledger chains validate and share decision
  `rc1-canary-human-confirmed` and proposal
  `rc1-canary-55d3609121062f574b92`.
- `terminal_trade_allowed=false`. The exact OANDA terminal process has remained
  running since `2026-08-22T16:10:00Z`, including before and after the CANARY;
  this rules out a terminal restart and wrong-instance diagnosis. The terminal
  journal does not record the actor that changed the toolbar permission, so a
  manual/external toggle is the supported explanation but is not asserted as
  conclusively attributable. ODIN did not alter it.

## Validation

- targeted temporal, gate, adapter, lifecycle, canary-contract and soak tests:
  `128 passed`;
- Ruff: passed;
- mypy directed scope: 7 source files, no issues;
- PowerShell syntax: passed;
- `git diff --check`: passed.

No new order, CANARY or broker submission was executed by this audit.
