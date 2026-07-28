# MT5 demo runbook

Preconditions: terminal detected; no real-account warning; verified DEMO secrets only in ignored local .env; guard/kill switch/restart/reconciliation/redaction/idempotency tests pass; explicit human login authorization exists.

Current phase: no login, order or account change. Adapter remains mock-only. Any future demo login uses bounded provider/global timeouts, Linux watchdog, telemetry and account confirmation; missing/unknown/real mode stops before terminal contact.
