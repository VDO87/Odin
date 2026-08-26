# ODIN DEMO CANARY PRE-FLIGHT

Status: **ODIN DEMO EXECUTION RC1 — CANARY READY — HUMAN CONFIRMATION REQUIRED**

Evidence captured: `2026-08-26T15:04:55Z`

This is a supervised pre-flight only. No DEMO or REAL order was sent. The
repository control remains disarmed with `canary_authorized=false`.

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
| SIDE | BUY, technical Stage 0 proposal only |
| VOLUME | 0.01 lot |
| SL | 1.16372 |
| TP | 1.16672 |
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
| DEMO_EXECUTION | ready; pre-submission only |
| HUMAN CANARY CONFIRMATION | required now; not granted |

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

## Mandatory human stop

All Stage 0 prerequisites are satisfied. The observed Stage 0 proposal was a
short-lived dry-run proposal; it does not itself authorize submission. Before
the first CANARY, ODIN must create and revalidate exactly one current proposal,
bind a short-lived one-shot authorization to that proposal and the verified
DEMO account fingerprint, and receive explicit human confirmation.

Do not repeat Stage 0 merely to keep a proposal alive. Do not call
`mt5.order_send` without the separate confirmation.

The next intended state is:

`CANARY READY — HUMAN CONFIRMATION REQUIRED`

with `broker_submission_called=false`.
