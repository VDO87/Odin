# ADR-001: isolated browser observation

## Decision

If the operator explicitly approves XTB observation later, ODIN will use only
Playwright Python behind a fixed-capability service bound to `127.0.0.1`. The
first code phase contains a fail-closed request guard only; Playwright is not
installed and XTB is not contacted.

## Boundaries

- Dedicated Chromium profile outside the personal Chrome profile.
- Local token, domain allowlist, redirect rejection, response-size/time limits.
- Fixed read-only capabilities: account summary, open positions, trade history.
- No arbitrary URL, input, script, upload, download, browser control, order, or
  financial action reaches Hermes.
- Authenticated content is redacted before local logs and is never sent to a
  cloud LLM.
- Rate limit, circuit breaker, kill switch, dry-run default, JSONL audit and
  health state are mandatory before the runtime can be enabled.

## Consequences

The service must fail closed for unavailable Playwright, missing local token,
unknown domains, redirect, timeout, malformed response, redaction failure and
any unrecognised capability. It cannot use the user's personal browser data or
become a general automation interface.
