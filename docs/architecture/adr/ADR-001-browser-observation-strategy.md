# ADR-001: browser observation

Use Playwright Python only after approval, behind a localhost service of fixed read-only capabilities. Hermes receives structured results only.

Controls: dedicated Chromium profile; local token; domain/redirect allowlist; redaction; timeouts; rate limit; circuit breaker; kill switch; dry-run; audit; negative tests. No generic navigation, input, JavaScript, financial action, personal Chrome or cloud LLM for authenticated data.

Playwright is not installed in this phase. MCP/CLI browser tools are development diagnostics only.
