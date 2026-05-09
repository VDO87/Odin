# ODIN RC1.6 Dashboard Visual Report

## 1. Estado inicial
- Branch: `release/rc1`
- Upstream: `origin/release/rc1`
- Base RC1.5: commit `1626bea`, tag `v0.1.5-rc1-soak-stability`
- Working tree inicial: limpo

## 2. Visual spec
Criado:
- `docs/design/ODIN_DASHBOARD_VISUAL_SPEC.md`

Resumo:
- estilo command center terminal/trading
- tema escuro monoespaçado
- painéis com borders
- alertas de segurança permanentes
- operador deve compreender estado em < 30s

## 3. Dashboard data provider
Criado módulo comum:
- `odin_dashboard/state_provider.py`
- `odin_dashboard/demo_state.py`
- `odin_dashboard/formatters.py`
- `odin_dashboard/security_badges.py`

Capacidades:
- leitura de snapshot/heartbeat/events/soak
- fallback para `DEMO DATA` quando snapshot real indisponível
- badges de segurança sempre visíveis
- redacção básica de chaves sensíveis
- resolução de caminhos `ODIN_HOME`
- readiness `ATLAS_PROFILE`

## 4. Dashboard TUI
Criado:
- `apps/dashboard_tui/app.py`
- `apps/dashboard_tui/layout.py`
- `apps/dashboard_tui/widgets.py`
- `apps/dashboard_tui/theme.py`

Comandos suportados:
- `python -m apps.dashboard_tui.app`
- `python -m apps.dashboard_tui.app --demo`
- `python -m apps.dashboard_tui.app --once`
- `python -m apps.dashboard_tui.app --smoke-test`

## 5. Dashboard HTML terminal theme
Actualizado:
- `apps/dashboard_html/app.py`
- `apps/dashboard_html/static/odin_terminal.css`
- `apps/dashboard_html/templates/*.html`

Páginas:
- `/`
- `/runtime`
- `/mt5`
- `/atlas`
- `/assistant`
- `/llm/status`
- `/logs`

Indicadores permanentes presentes:
- `TRADING REAL: BLOCKED`
- `MT5 ORDER_SEND: BLOCKED`
- `BROKER REAL: BLOCKED`
- `ATLAS: SHADOW_ONLY`
- `LLM: READ_ONLY`

## 6. Dashboard preview
Implementado:
- `python -m apps.dashboard_html.app --export-preview`

Output:
- `dashboard_preview/index.html`
- `dashboard_preview/runtime.html`
- `dashboard_preview/mt5.html`
- `dashboard_preview/atlas.html`
- `dashboard_preview/assistant.html`
- `dashboard_preview/logs.html`
- `dashboard_preview/README_PREVIEW.md`

## 7. Dashboard QA
Implementado:
- `python -m apps.dashboard_html.app --dashboard-qa`

Relatório:
- `docs/reports/ODIN_DASHBOARD_VISUAL_QA_REPORT.md`
- Estado final: **PASS**
- Endpoints essenciais: OK
- Tokens críticos de segurança: presentes
- Tokens perigosos (ordem real): ausentes

## 8. ODIN_HOME readiness
Actualizado em `.env.example`:
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

## 9. LLM readiness
Criado:
- `docs/runbooks/LLM_INSTALLATION_READINESS.md`
- `services/ollama-override.example`

Regras mantidas:
- sem instalação automática de modelos
- OpenAI OFF por defeito
- fallback seguro

## 10. ATLAS profile readiness
Actualizado `.env.example` com:
- `ATLAS_PROFILE`
- `ATLAS_LITE_ENABLED`
- `ATLAS_FULL_ENABLED`
- `ATLAS_DEFAULT_PROFILE`
- `ATLAS_LITE_MAX_AGENTS`
- `ATLAS_FULL_MAX_AGENTS`

Criado:
- `docs/runbooks/ATLAS_PROFILE.md`

## 11. Scripts e CLI
Actualizado `run_odin.sh`:
- `--dashboard`
- `--dashboard-preview`
- `--dashboard-qa`
- `--tui`
- `--tui-demo`
- `--tui-once`
- `--tui-smoke-test`

Actualizado `apps/dashboard_terminal/cli.py`:
- `dashboard-preview`
- `dashboard-qa`
- `tui-smoke-test`
- `tui-once`
- `tui-demo`

## 12. Testes criados/actualizados
Novos testes:
- `tests/unit/test_dashboard_state_provider.py`
- `tests/unit/test_dashboard_demo_state.py`
- `tests/unit/test_dashboard_tui_smoke.py`
- `tests/unit/test_dashboard_html_terminal_theme.py`
- `tests/unit/test_dashboard_export_preview.py`
- `tests/unit/test_dashboard_visual_qa.py`
- `tests/unit/test_run_odin_dashboard_modes.py`
- `tests/unit/test_odin_home_paths.py`
- `tests/unit/test_atlas_profile_config.py`
- `tests/unit/test_llm_installation_readiness.py`

## 13. CI
Actualizado `.github/workflows/ci.yml` com:
- `python -m apps.dashboard_html.app --dashboard-qa`
- `python -m apps.dashboard_tui.app --smoke-test`
- `./run_odin.sh --dashboard-preview`
- `./run_odin.sh --tui-smoke-test`

## 14. Validação executada
- `pytest -q` -> **215 passed**
- `ruff check .` -> **passed**
- `mypy .` -> **passed**
- `python -m apps.dashboard_html.app --smoke-test` -> OK
- `python -m apps.dashboard_html.app --export-preview` -> OK
- `python -m apps.dashboard_html.app --dashboard-qa` -> PASS
- `python -m apps.dashboard_tui.app --smoke-test` -> OK
- `python -m apps.dashboard_tui.app --once --demo` -> OK
- `./run_odin.sh --dashboard-preview` -> OK
- `./run_odin.sh --dashboard-qa` -> PASS
- `./run_odin.sh --tui-smoke-test` -> OK
- `./run_odin.sh --tui-once` -> OK

## 15. Segurança (confirmada)
- trading real bloqueado: **SIM**
- MT5 order_send bloqueado: **SIM**
- XTB real bloqueado: **SIM**
- broker real bloqueado: **SIM**
- LLM sem execução directa: **SIM**
- ATLAS sem execução directa: **SIM**
