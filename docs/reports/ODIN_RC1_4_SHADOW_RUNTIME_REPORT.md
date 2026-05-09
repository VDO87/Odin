# ODIN RC1.4 Shadow Runtime Report

## 1. Estado inicial
- Diretório: `/home/vdo/Secretária/Projects_Codex/Odin_Teste`
- Branch: `release/rc1`
- Upstream: `origin/release/rc1`
- Commit inicial: `3a17dec`
- Tag base: `v0.1.3-rc1-local-llm`
- Working tree inicial: limpo.

## 2. Ficheiros alterados
- `.env.example`
- `.github/workflows/ci.yml`
- `.gitignore`
- `README.md`
- `run_odin.sh`
- `config/question_registry.yaml`
- `apps/dashboard_html/app.py`
- `apps/dashboard_terminal/cli.py`
- `apps/telegram_bot/bot.py`
- `odin_assistant/assistant_router.py`
- `odin_assistant/context_builder.py`
- `odin_assistant/intent_classifier.py`
- `odin_atlas/coordinator.py`
- `odin_control/command_bus.py`
- `odin_control/system_controller.py`
- `odin_core/__init__.py`
- `odin_core/runtime.py`
- `odin_health/healthcheck.py`
- `docs/reports/ODIN_RC1_4_SHADOW_RUNTIME_REPORT.md`

## 3. Ficheiros criados
- `odin_core/runtime_state.py`
- `odin_core/events.py`
- `odin_core/heartbeat.py`
- `odin_core/orchestrator.py`
- `odin_health/checks_runtime.py`
- `docs/runbooks/SHADOW_RUNTIME_LOOP.md`
- `tests/unit/test_runtime_orchestrator.py`
- `tests/unit/test_runtime_state_snapshot.py`
- `tests/unit/test_runtime_events.py`
- `tests/unit/test_runtime_command_bus.py`
- `tests/unit/test_runtime_dashboard_smoke.py`
- `tests/unit/test_runtime_cli_commands.py`
- `tests/unit/test_runtime_telegram_dry_run.py`
- `tests/unit/test_runtime_assistant_context.py`
- `tests/unit/test_runtime_atlas_shadow_cycle.py`
- `tests/unit/test_run_odin_runtime_modes.py`

## 4. Runtime Orchestrator
- Implementado `ShadowRuntimeOrchestrator` com:
  - `start()`, `stop()`, `pause()`, `resume()`, `run_once()`, `run_loop()`, `get_status()`, `safe_shutdown()`.
- Estados runtime suportados:
  - `STOPPED`, `STARTING`, `RUNNING`, `PAUSED`, `DEGRADED`, `BLOCKED`, `RECOVERY_MODE`, `STOPPING`, `KILLED`.
- `run_once()` faz heartbeat, healthcheck periódico, MT5 shadow poll/reconciliation, contexto assistant, ciclo ATLAS shadow, snapshot e eventos.
- Sem execução de ordens.

## 5. Heartbeat
- Arquivo: `data/runtime/odin_heartbeat.json`.
- Logs:
  - `logs/system/heartbeat.log`
- Evento: `HEARTBEAT`.

## 6. Snapshot
- Arquivo: `data/runtime/odin_state_snapshot.json`.
- Conteúdo inclui:
  - estado runtime, modo, flags de segurança (`trading_real_enabled=false`, `mt5_order_send_enabled=false`, etc.), health, mt5, positions, atlas, assistant, llm, últimos erros/eventos.
- Redacção aplicada para dados sensíveis.

## 7. Event Log
- Arquivo: `data/runtime/odin_events.jsonl`.
- Logs adicionais:
  - `logs/system/runtime.log`
  - `logs/system/events.log`
  - `logs/errors/runtime_errors.log`
- Eventos operacionais implementados:
  - `RUNTIME_STARTED`, `RUNTIME_STOPPED`, `RUNTIME_PAUSED`, `RUNTIME_RESUMED`
  - `HEARTBEAT`
  - `HEALTHCHECK_OK`, `HEALTHCHECK_WARNING`, `HEALTHCHECK_BLOCKED`, `HEALTHCHECK_CRITICAL`
  - `MT5_STATUS_UPDATED`, `MT5_RECONCILIATION_DONE`
  - `ATLAS_SHADOW_CYCLE_DONE`
  - `ASSISTANT_CONTEXT_UPDATED`
  - `RECOVERY_STARTED`, `RECOVERY_COMPLETED`
  - `COMMAND_RECEIVED`, `COMMAND_BLOCKED`
  - `ERROR`

## 8. Dashboard runtime
- Nova rota: `/runtime`.
- Exposição de:
  - runtime status, snapshot, eventos e safe_to_trade.
- Botões runtime (via Command Bus):
  - Runtime Status, Run Once, Runtime Pause, Runtime Resume, Safe Shutdown, Snapshot.
- Smoke-test atualizado para validar:
  - `/`, `/runtime`, `/assistant`, `/llm/status`, `/atlas`, `/mt5`, `/logs`.

## 9. CLI runtime
- Novos comandos:
  - `runtime-status`
  - `runtime-run-once`
  - `runtime-pause`
  - `runtime-resume`
  - `runtime-stop`
  - `runtime-snapshot`
  - `runtime-events`
  - `runtime-smoke-test`
- Comandos runtime passam via Command Bus.

## 10. Telegram runtime
- Novos comandos runtime:
  - `/runtime`
  - `/runtime_status`
  - `/runtime_snapshot`
  - `/runtime_events`
  - `/runtime_pause`
  - `/runtime_resume`
- `--dry-run` valida sem token/sem chamadas externas.

## 11. Assistant runtime
- Novas perguntas runtime suportadas:
  - estado runtime, heartbeat, bloqueio, snapshot, eventos, sombra/soak test.
- Contexto inclui snapshot/eventos/health/mt5/atlas com redacção de sensíveis.

## 12. ATLAS shadow cycle
- `AtlasCoordinator.run_shadow_cycle(context)` adicionado.
- Sempre devolve `execution_permission="SHADOW_ONLY"` e `atlas_executes_orders=false`.
- Sem dados suficientes -> `WARNING`, sem inventar sinais.

## 13. Healthcheck runtime
- `checks_runtime` adicionado e integrado no healthcheck global:
  - valida escrita de snapshot/heartbeat/events;
  - valida runtime config;
  - expõe estado estruturado.

## 14. Run scripts
- `run_odin.sh` atualizado com:
  - `--runtime`
  - `--run-once`
  - `--runtime-smoke-test`
  - `--snapshot`
- Defaults seguros preservados.

## 15. Testes
- `pytest -q` -> **196 passed**
- `ruff check .` -> **All checks passed**
- `mypy .` -> **Success: no issues found in 205 source files**
- `python -m apps.dashboard_html.app --smoke-test` -> **OK**
- `python -m apps.dashboard_terminal.cli smoke-test` -> **OK**
- `python -m apps.telegram_bot.bot --dry-run` -> **OK**
- `./run_odin.sh --runtime-smoke-test` -> **OK**
- `./run_odin.sh --run-once` -> **OK**

## 16. Segurança
- trading real bloqueado;
- MT5 order_send bloqueado;
- XTB real bloqueado;
- broker real bloqueado;
- LLM sem execução directa;
- ATLAS sem execução directa;
- runtime sem execução real.
