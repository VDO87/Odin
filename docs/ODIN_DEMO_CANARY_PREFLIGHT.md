# ODIN DEMO CANARY PRE-FLIGHT

Status: **ODIN DEMO EXECUTION RC1 — CANARY LIFECYCLE COMPLETE AND RECONCILED**

CANARY evidence captured: `2026-08-28T09:14:46Z`

The reviewed pre-flight was followed by explicit human confirmation for one
DEMO CANARY. The repository control remains disarmed with
`canary_authorized=false`; authority was short-lived, proposal-specific and
consumed once.

## Pre-flight

| Check | Observed |
|---|---|
| ACCOUNT | DEMO |
| BROKER | OANDA TMS Brokers S.A. |
| SERVER | OANDATMS-MT5 |
| TERMINAL | `C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe` process verified; `terminal_info.path` is the containing directory |
| TERMINAL CONNECTED | true |
| BALANCE | EUR 50,000.00 DEMO |
| EQUITY | EUR 50,000.00 DEMO |
| SYMBOL | EURUSD |
| SIDE | BUY, one confirmed CANARY |
| VOLUME | 0.01 lot |
| REQUESTED / EXECUTED PRICE | 1.16437 / 1.16437 |
| SL | 1.16337 |
| TP | 1.16637 |
| MAX LOSS ESTIMATED | EUR 0.86 DEMO |
| RISK STATUS | ALLOW_DEMO |
| RISK REASONS | none |
| DATA FRESHNESS | FRESH; 7 seconds |
| RECONCILIATION | RECONCILED |
| TERMINAL TRADE STATE | `terminal_trade_allowed=true` on the verified OANDATMS-MT5 DEMO terminal |
| ORDER CHECK | ACCEPTED; retcode `0`, comment `Done` |
| REAL_TRADING | false |
| SAFE_TO_TRADE | false |
| EXECUTION_ALLOWED | false |
| DEMO_EXECUTION | one-shot consumed; new execution disabled |
| HUMAN CANARY CONFIRMATION | explicitly granted and consumed for one proposal |

The requested executable, DEMO account mode, broker, server and configured
login all matched. No password or account identifier was printed or persisted
in this report.

## Stage 0 evidence

- Runtime: `D:\ODIN_LOCAL\runtime\mt5_probe_venv\Scripts\python.exe`
- Raw report: `D:\ODIN_LOCAL\reports\demo-execution\stage0-dry-run.json`
- Raw report SHA-256:
  `85ac8d9d5e2aeb779137dc3588ed01fb1865c51ecb6c4abb5498746d94ba012d`
- Result: `DRY_RUN_VALIDATED`; normalized data FRESH, Risk `ALLOW_DEMO`,
  reconciliation `RECONCILED`, `order_check` accepted.
- Broker submission called: false.

## CANARY outcome

- Proposal: `rc1-canary-55d3609121062f574b92`
- Decision: `rc1-canary-human-confirmed`
- Submission: `FILLED`, retcode `10009`
- Order/position id: `151407246`
- Deal: `105358964`
- Executed volume: 0.01 lot
- Slippage: 0 points
- Broker reconciliation: `RECONCILED`
- Execution Ledger: hash chain valid; final state `CLOSED / RECONCILED`
- Raw report: `D:\ODIN_LOCAL\reports\demo-execution\canary-one-shot.json`
- Raw report SHA-256:
  `74f891b5c7b7fa707e176855e58cee207f4e7a40836d13da7676dbd1ef115d18`
- One-shot attempt marker: present
- New broker submission allowed: false

MT5 history proves that the position closed at SL: exit deal `105378769`, order
`151427905`, normalized close time `2026-08-28T14:01:42Z`, exit price 1.16335
and realized P/L EUR -0.88. Commission, swap and fee were zero. The DEMO
Decision Ledger and Execution Ledger are hash-valid and linked by decision,
proposal and position identifiers. Do not open a second position.

The next intended state is:

`CANARY LIFECYCLE COMPLETE_AND_RECONCILED`

with exactly one historical `broker_submission_called=true` and no new broker
action enabled.
