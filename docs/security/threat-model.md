# Threat model ODIN/Hermes

Assets: broker credentials, cookies, tokens, SQLite, logs, market data, config and execution control.

Boundaries: Hermes read-only; Risk blocks; adapters isolated; dashboard localhost; Codex changes reviewed by humans.

Controls: ignored .env and redaction; dedicated browser profile/allowlist/local token; remote content treated as untrusted data; flags false plus future idempotency/kill switch; demo-only guard; timeout/cache/freshness gates; lockfile/hash/license/scan before dependencies; no cloud fallback for authenticated data.

Residual risk: WSL visibility depends on elevation. No demo transition without documented controls and tests.
