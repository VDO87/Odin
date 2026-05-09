# ODIN

ODIN é uma plataforma local para decisão operacional, supervisão, auditoria e diagnóstico em trading assistido.

## Estado atual
- Release: **RC1.6 Dashboard Visual Command Center**
- Branch principal: `release/rc1`
- Modo operacional de referência: `SHADOW_MT5`

## Segurança (bloqueios ativos)
- Trading real bloqueado.
- `MT5 order_send` bloqueado.
- XTB real bloqueado.
- Broker real bloqueado.
- LLM sem execução direta.
- ATLAS sem execução direta.
- Runtime sem execução real.
- OpenAI desligada por defeito.

## Componentes RC1
- `odin_control`
- `odin_core`
- `odin_health`
- `odin_assistant`
- `odin_atlas`
- `odin_execution`
- `odin_brokers`
- Dashboard HTML (`apps/dashboard_html`)
- CLI terminal (`apps/dashboard_terminal`)
- Telegram bot (`apps/telegram_bot`)
- Dashboard TUI (`apps/dashboard_tui`)
- Dashboard state provider (`odin_dashboard`)

## Dashboard Visual Command Center
RC1.6 introduz dashboard visual estilo terminal (HTML + TUI), com foco operacional:
- top bar de estado
- badges de segurança permanentes
- runtime/MT5/ATLAS/LLM/risk/positions/events
- command bar apenas com comandos seguros
- preview estático e QA visual automatizado

### Comandos dashboard/TUI
```bash
./run_odin.sh --dashboard
./run_odin.sh --dashboard-preview
./run_odin.sh --dashboard-qa
./run_odin.sh --tui
./run_odin.sh --tui-demo
./run_odin.sh --tui-once
./run_odin.sh --tui-smoke-test
python -m apps.dashboard_html.app --export-preview
python -m apps.dashboard_html.app --dashboard-qa
python -m apps.dashboard_tui.app --smoke-test
```

### Dashboard preview
- Pasta: `dashboard_preview/` (ou `ODIN_DASHBOARD_PREVIEW_DIR`)
- Conteúdo: `index.html`, `runtime.html`, `mt5.html`, `atlas.html`, `assistant.html`, `logs.html`

## ODIN_HOME Readiness
`.env.example` inclui paths para instalação em pasta única (preparação RC1.7):
- `ODIN_HOME`
- `ODIN_APP_DIR`
- `ODIN_CONFIG_DIR`
- `ODIN_DATA_DIR`
- `ODIN_LOG_DIR`
- `ODIN_MODELS_DIR`
- `ODIN_VENDOR_DIR`
- `ODIN_BACKUP_DIR`
- `ODIN_TMP_DIR`
- `ODIN_DASHBOARD_PREVIEW_DIR`

## ATLAS Profile Readiness
- `ATLAS_PROFILE=lite|full`
- Lite recomendado para runtime contínuo.
- Full recomendado para análise manual detalhada.
- Ambos permanecem `SHADOW_ONLY`.

## LLM Installation Readiness
- RC1.6 não instala modelos automaticamente.
- Preparado para `OLLAMA_MODELS=${ODIN_MODELS_DIR}/ollama`.
- OpenAI continua OFF por defeito.

## Shadow Runtime Loop
O runtime em sombra mantém heartbeat, healthchecks periódicos, snapshot de estado e eventos observáveis sem executar ordens.

### Comandos runtime
```bash
./run_odin.sh --runtime
./run_odin.sh --run-once
./run_odin.sh --runtime-smoke-test
./run_odin.sh --snapshot
python -m apps.dashboard_terminal.cli runtime-status
python -m apps.dashboard_terminal.cli runtime-run-once
python -m apps.dashboard_terminal.cli runtime-snapshot
python -m apps.dashboard_terminal.cli runtime-events
python -m apps.dashboard_terminal.cli runtime-validate
python -m apps.dashboard_terminal.cli soak-test --mini
python -m apps.dashboard_terminal.cli soak-report
```

### Snapshot e eventos
- Snapshot: `data/runtime/odin_state_snapshot.json`
- Heartbeat: `data/runtime/odin_heartbeat.json`
- Eventos: `data/runtime/odin_events.jsonl`
- Soak result: `data/runtime/soak_tests/latest_soak_result.json`

## Soak Test & Estabilidade
- Runner: `tools/odin_soak_test.py`
- Valida heartbeat/snapshot/eventos/logs/comandos e bloqueios de segurança.
- Falha imediata se detectar tentativa de ordem.

### Comandos soak
```bash
./run_odin.sh --runtime-validate
./run_odin.sh --soak-test-mini
./run_odin.sh --soak-test
./run_odin.sh --soak-report
python -m apps.dashboard_terminal.cli runtime-validate
python -m apps.dashboard_terminal.cli soak-test --mini
python -m apps.dashboard_terminal.cli soak-report
```

## Local LLM Assistant
- Provider suportado: `ollama` (opcional).
- Uso: respostas operacionais, explicação de estado e apoio a análise/critica.
- Se indisponível, o Assistant usa fallback seguro sem crash.
- O LLM não executa ordens, não altera configurações críticas e não ignora Command Bus/Risk Engine.

## Como testar (offline/safe)
```bash
./install.sh --dry-run
./healthcheck.sh --offline-ok
./run_odin.sh --smoke-test
./run_odin.sh --runtime-smoke-test
./run_odin.sh --run-once
./run_odin.sh --runtime-validate
./run_odin.sh --soak-test-mini
./run_odin.sh --dashboard-preview
./run_odin.sh --dashboard-qa
./run_odin.sh --tui-smoke-test
./run_odin.sh --tui-once
python -m apps.dashboard_html.app --smoke-test
python -m apps.dashboard_terminal.cli smoke-test
python -m apps.telegram_bot.bot --dry-run
```

## Runbooks
- MT5 Shadow: [docs/runbooks/MT5_SHADOW_MODE.md](docs/runbooks/MT5_SHADOW_MODE.md)
- Local LLM Runtime: [docs/runbooks/LOCAL_LLM_RUNTIME.md](docs/runbooks/LOCAL_LLM_RUNTIME.md)
- Shadow Runtime Loop: [docs/runbooks/SHADOW_RUNTIME_LOOP.md](docs/runbooks/SHADOW_RUNTIME_LOOP.md)
- Soak Runtime Stability: [docs/runbooks/SOAK_TEST_RUNTIME_STABILITY.md](docs/runbooks/SOAK_TEST_RUNTIME_STABILITY.md)
- Dashboard Testing: [docs/runbooks/DASHBOARD_TESTING.md](docs/runbooks/DASHBOARD_TESTING.md)
- ATLAS Profile: [docs/runbooks/ATLAS_PROFILE.md](docs/runbooks/ATLAS_PROFILE.md)
- LLM Installation Readiness: [docs/runbooks/LLM_INSTALLATION_READINESS.md](docs/runbooks/LLM_INSTALLATION_READINESS.md)

## Aviso
ODIN RC1 **não executa dinheiro real**.
