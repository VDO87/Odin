# Secrets management

Copy .env.example to .env only inside local WSL. Never place .env, cookies, tokens, authenticated captures, SQLite dumps or credentials in Git, prompts, dashboard, reports or D: archives.

Use only names in documentation: ODIN_MT5_LOGIN, ODIN_MT5_PASSWORD, ODIN_MT5_SERVER, ODIN_MT5_ACCOUNT_MODE and read-only provider keys. Validate shape without printing values and redact before JSONL/SQLite. If exposed: stop, revoke/rotate, remove the local artifact and record an incident.
