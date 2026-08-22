# ADR-005: MT5 demo adapter

The accepted observation baseline was mock/read-only. ODIN DEMO EXECUTION RC1
may now build an isolated DEMO adapter, inspect the already configured terminal,
run `order_check`, and prepare exactly one guarded `order_send` call. It must not
change credentials, select or fall back to another account, or contact a REAL
or UNKNOWN account for execution.

Gate: environment hints are never sufficient proof. Terminal/account evidence
must deterministically match the expected DEMO identity; missing, unknown, REAL
and mismatch hard-block. Secrets stay in ignored local `.env` and are never
logged or persisted. Kill switch, limits, idempotency, reconciliation, retcodes,
restart recovery and redaction are mandatory. `order_check` does not replace
Risk approval. The first DEMO `order_send` needs a complete PRE-FLIGHT plus a
separate one-shot human CANARY confirmation. AIOMQL is not adopted.

Decision: the single execution call is confined to
`src/odin/adapters/mt5/demo_execution_adapter.py`; all upstream components are
broker-agnostic and cannot invoke it. `real_trading=false` remains immutable.
