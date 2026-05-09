# ODIN RC1.7 Install Validation Report

- Timestamp: `2026-05-09T21:04:12.561605+00:00`
- Status: `PASS`
- Dry-run: `True`
- ODIN_HOME: `/tmp/ODIN_RUNTIME_TEST`

## Path checks
- path:/tmp/ODIN_RUNTIME_TEST: OK
- path:/tmp/ODIN_RUNTIME_TEST/app: OK
- path:/tmp/ODIN_RUNTIME_TEST/.venv: OK
- path:/tmp/ODIN_RUNTIME_TEST/config: OK
- path:/tmp/ODIN_RUNTIME_TEST/data: OK
- path:/tmp/ODIN_RUNTIME_TEST/data/runtime: OK
- path:/tmp/ODIN_RUNTIME_TEST/data/memory: OK
- path:/tmp/ODIN_RUNTIME_TEST/data/market: OK
- path:/tmp/ODIN_RUNTIME_TEST/data/backtests: OK
- path:/tmp/ODIN_RUNTIME_TEST/data/soak_tests: OK
- path:/tmp/ODIN_RUNTIME_TEST/logs: OK
- path:/tmp/ODIN_RUNTIME_TEST/logs/system: OK
- path:/tmp/ODIN_RUNTIME_TEST/logs/health: OK
- path:/tmp/ODIN_RUNTIME_TEST/logs/control: OK
- path:/tmp/ODIN_RUNTIME_TEST/logs/assistant: OK
- path:/tmp/ODIN_RUNTIME_TEST/logs/atlas: OK
- path:/tmp/ODIN_RUNTIME_TEST/logs/market: OK
- path:/tmp/ODIN_RUNTIME_TEST/logs/trading: OK
- path:/tmp/ODIN_RUNTIME_TEST/logs/telegram: OK
- path:/tmp/ODIN_RUNTIME_TEST/logs/brokers: OK
- path:/tmp/ODIN_RUNTIME_TEST/logs/errors: OK
- path:/tmp/ODIN_RUNTIME_TEST/models: OK
- path:/tmp/ODIN_RUNTIME_TEST/models/ollama: OK
- path:/tmp/ODIN_RUNTIME_TEST/vendor: OK
- path:/tmp/ODIN_RUNTIME_TEST/vendor/wheels: OK
- path:/tmp/ODIN_RUNTIME_TEST/vendor/atlas: OK
- path:/tmp/ODIN_RUNTIME_TEST/vendor/llm: OK
- path:/tmp/ODIN_RUNTIME_TEST/services: OK
- path:/tmp/ODIN_RUNTIME_TEST/backups: OK
- path:/tmp/ODIN_RUNTIME_TEST/dist: OK
- path:/tmp/ODIN_RUNTIME_TEST/dashboard_preview: OK
- path:/tmp/ODIN_RUNTIME_TEST/tmp: OK

## Command checks
- /tmp/ODIN_RUNTIME_TEST/app/run_odin.sh --runtime-smoke-test: DRY_RUN (rc=0)
- /tmp/ODIN_RUNTIME_TEST/app/run_odin.sh --run-once: DRY_RUN (rc=0)
- /tmp/ODIN_RUNTIME_TEST/app/run_odin.sh --runtime-validate: DRY_RUN (rc=0)
- /tmp/ODIN_RUNTIME_TEST/app/run_odin.sh --soak-test-mini: DRY_RUN (rc=0)
- /tmp/ODIN_RUNTIME_TEST/app/run_odin.sh --dashboard-preview: DRY_RUN (rc=0)
- /tmp/ODIN_RUNTIME_TEST/app/run_odin.sh --dashboard-qa: DRY_RUN (rc=0)
- /tmp/ODIN_RUNTIME_TEST/app/run_odin.sh --tui-smoke-test: DRY_RUN (rc=0)
- /tmp/ODIN_RUNTIME_TEST/app/scripts/check_llm_runtime.sh: DRY_RUN (rc=0)
- /tmp/ODIN_RUNTIME_TEST/app/scripts/check_atlas_profile.sh: DRY_RUN (rc=0)
