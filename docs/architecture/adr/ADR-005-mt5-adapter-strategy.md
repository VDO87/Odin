# ADR-005: MT5 demo adapter

Current state is mock-only. A future phase may detect the local terminal and validate account mode, but cannot login, read authenticated data, send, modify or cancel orders.

Gate: ODIN_MT5_ACCOUNT_MODE=demo is required; missing, unknown and real block. Secrets stay in ignored local .env. Before any future login, kill switch, idempotency, reconciliation, retcodes, restart and redaction must be tested. Demo login needs verified DEMO credentials and separate human authorization. AIOMQL is not adopted.
