# ODIN RC1.8 Local Runtime Installation Report

## 1) Estado inicial
- Branch: `release/rc1`
- Upstream: `origin/release/rc1`
- Commit base: `b843f0e`
- Tag base: `v0.1.7-rc1-deployment-package`
- Working tree inicial: limpo
- Package confirmado: `dist/odin-rc1.7-deployment-package.tar.gz`

## 2) Pasta instalada
- Target: `~/ODIN_RUNTIME`
- Situação prévia: **não existia** (`MISSING`)
- Backup pré-instalação: não aplicável

## 3) Estrutura criada
Estrutura validada sob `~/ODIN_RUNTIME`:
- `app/`
- `.venv/`
- `config/`
- `data/` (`runtime/`, `memory/`, `market/`, `backtests/`, `soak_tests/`)
- `logs/` (`system/`, `health/`, `control/`, `assistant/`, `atlas/`, `market/`, `trading/`, `telegram/`, `brokers/`, `errors/`)
- `models/ollama/`
- `vendor/` (`wheels/`, `atlas/`, `llm/`)
- `services/`
- `backups/`
- `dist/`
- `dashboard_preview/`
- `tmp/`

## 4) Resultado install
Comando:
```bash
./scripts/install_odin_runtime.sh --odin-home ~/ODIN_RUNTIME --copy-current-app
```
Resultado: **OK**
- runtime layout criado
- app copiada para `~/ODIN_RUNTIME/app`
- `~/ODIN_RUNTIME/config/.env` criado
- `~/ODIN_RUNTIME/.venv` criado
- dependências tentadas
- symlinks runtime preparados
- runtime smoke tentado

## 5) Resultado validate runtime
Comando:
```bash
./scripts/validate_odin_runtime.sh --odin-home ~/ODIN_RUNTIME
```
Resultado: **PASS**
- JSON: `~/ODIN_RUNTIME/data/runtime/install_validation_report.json`
- Resumo: [ODIN_RC1_8_INSTALL_VALIDATION_RESULT.md](/home/vdo/Secretária/Projects_Codex/Odin_Teste/docs/reports/ODIN_RC1_8_INSTALL_VALIDATION_RESULT.md)

## 6) Resultado run_odin na pasta instalada
Executado em `~/ODIN_RUNTIME/app`:
- `./run_odin.sh --runtime-smoke-test` -> OK
- `./run_odin.sh --run-once` -> OK
- `./run_odin.sh --runtime-validate` -> PASS
- `./run_odin.sh --soak-test-mini` -> PASS
- `./run_odin.sh --dashboard-preview` -> OK
- `./run_odin.sh --dashboard-qa` -> PASS
- `./run_odin.sh --tui-smoke-test` -> OK
- `./run_odin.sh --tui-once` -> OK

## 7) Resultado dashboard
Teste real de servidor:
- comando `./run_odin.sh --dashboard`
- URL: `http://127.0.0.1:8000`
- Endpoints validados por curl:
  - `/` -> 200
  - `/runtime` -> 200
  - `/mt5` -> 200
  - `/atlas` -> 200
  - `/assistant` -> 200
  - `/llm/status` -> 200
  - `/logs` -> 200

Nota de ambiente: no sandbox sem elevação houve `PermissionError` no bind de socket; com validação no host elevável os endpoints responderam 200.

## 8) Resultado TUI
Executado:
- `./run_odin.sh --tui-demo` -> OK
- `./run_odin.sh --tui-once` -> OK

Observado:
- runtime visível
- MT5 visível
- ATLAS visível
- LLM visível
- Risk visível
- security strip visível
- sem comandos perigosos

## 9) Resultado LLM readiness
Comando:
```bash
./scripts/check_llm_runtime.sh --odin-home ~/ODIN_RUNTIME
```
Resultado: `WARNING` (esperado em ambiente sem Ollama/modelo)
- `ollama_installed=false`
- `endpoint_reachable=false`
- `model_configured=false`
- `fallback_active=true`
- sem instalação automática de modelos

## 10) Resultado ATLAS readiness
Comando:
```bash
./scripts/check_atlas_profile.sh --odin-home ~/ODIN_RUNTIME
```
Resultado: `OK`
- `ATLAS_ENABLED=true`
- `ATLAS_PROFILE=lite`
- `execution_permission=SHADOW_ONLY`
- agentes lite disponíveis

## 11) Resultado Telegram dry-run
Comando:
```bash
python -m apps.telegram_bot.bot --dry-run
```
Resultado: **OK**
- sem token real (`token_present=false`)
- não enviou mensagens reais (`network_calls=not_performed`)
- comandos listados
- safe mode ativo

## 12) Resultado backup
Comando:
```bash
./scripts/backup_odin_runtime.sh --odin-home ~/ODIN_RUNTIME
```
Resultado: **OK**
- backup criado em `~/ODIN_RUNTIME/backups/odin_runtime_backup_20260509_213046.tar.gz`
- verificação de conteúdo: sem `.venv`, sem `tmp`, sem `__pycache__`, sem `models/` pesados por defeito

## 13) Resultado update dry-run
Comando:
```bash
./scripts/update_odin_runtime.sh --odin-home ~/ODIN_RUNTIME --dry-run --backup-first
```
Resultado: **OK**
- detectou instalação
- preserva `.env` (não sobrescreve)
- lista ações previstas

## 14) Resultado uninstall dry-run
Comando:
```bash
./scripts/uninstall_odin_runtime.sh --odin-home ~/ODIN_RUNTIME --dry-run
```
Resultado: **OK**
- não apagou dados
- mostrou o que removeria
- mantém defaults seguros (`keep data/logs/config`)

## 15) Estado de segurança
Verificado em `~/ODIN_RUNTIME/config/.env`:
- `ENABLE_REAL_TRADING=false`
- `ENABLE_AUTO_EXECUTION=false`
- `MT5_ORDER_SEND_ENABLED=false`
- `XTB_REAL_ENABLED=false`
- `BROKER_ALLOW_REAL_EXECUTION=false`
- `OPENAI_SUPPORT_ENABLED=false`

Confirmação:
- sem trading real
- sem `order_send`
- sem broker real
- sem execução de ordens

## 16) Pendências
- Ollama instalado: **não**
- MT5 instalado/biblioteca disponível: **não**
- Telegram configurado (token/user ids): **não**
- systemd configurado: **não** (apenas templates)
