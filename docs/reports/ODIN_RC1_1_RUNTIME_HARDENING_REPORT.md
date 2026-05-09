# ODIN RC1.1 Runtime Hardening Report

Date: 2026-05-09

## 1. Alterações feitas
- `apps/dashboard_html/app.py`
  - Refactor para `create_app()`.
  - Separação entre criação da app e bind de servidor.
  - Novo `--smoke-test` sem socket/bind.
  - Novo endpoint `GET /api/healthcheck`.
- `run_odin.sh`
  - Deteção de Python em ordem: `.venv/bin/python`, `python3`, `python`.
  - Mensagem clara se Python ausente.
  - Novos modos: `--smoke-test`, `--dashboard`, `--healthcheck`.
  - Defaults de segurança reforçados (`SHADOW_MT5`, bloqueios de execução real).
- `healthcheck.sh`
  - Deteção robusta de Python.
  - Novo `--offline-ok`.
  - Saída explícita com `FINAL_STATUS=...`.
- `install.sh`
  - Deteção de rede antes de instalação PyPI.
  - Mensagem clara em ausência de rede.
  - Logging em `logs/system/install.log`.
  - Novo `--dry-run`.
  - Novo `--offline` com suporte a `vendor/wheels` ou `wheelhouse`.
- `apps/dashboard_terminal/cli.py`
  - Novo comando `smoke-test`.
- `apps/telegram_bot/bot.py`
  - Novo `--dry-run` sem contacto externo.
- `odin_health/checks_network.py`
  - Diagnóstico mais claro de rede/DNS/permissões/sandbox/timeout.
  - `reason`, `check`, `safe_to_trade`, `details`.

## 2. Problemas corrigidos
1. Dependência cega de `python` no PATH (scripts agora autodetetram Python).
2. Falhas opacas de instalação sem rede (agora mensagem explícita + log).
3. Falta de validação sem bind no dashboard (agora `--smoke-test`).
4. Falta de modo offline tolerante no healthcheck (agora `--offline-ok`).
5. Falta de dry-run no bot Telegram e smoke-test na CLI.

## 3. Scripts actualizados
- `run_odin.sh`
- `healthcheck.sh`
- `install.sh`

## 4. Novos comandos disponíveis
- `python -m apps.dashboard_html.app --smoke-test`
- `./run_odin.sh --smoke-test`
- `./run_odin.sh --dashboard`
- `./run_odin.sh --healthcheck`
- `./healthcheck.sh --offline-ok`
- `./install.sh --dry-run`
- `./install.sh --offline`
- `python -m apps.dashboard_terminal.cli smoke-test`
- `python -m apps.telegram_bot.bot --dry-run`

## 5. Resultado dos testes
- `pytest -q`: `160 passed`
- `ruff check .`: `All checks passed`
- `mypy .`: `Success: no issues found in 168 source files`

## 6. Estado do dashboard smoke-test
- Executado com sucesso.
- Resultado: `Dashboard smoke-test OK`.
- Sem bind de socket.

## 7. Estado do install dry-run
- Executado com sucesso.
- Validação estrutural concluída sem instalar dependências.
- Log gravado em `logs/system/install.log`.

## 8. Estado do healthcheck offline-ok
- Executado com sucesso em ambiente sem rede.
- Resultado final: `FINAL_STATUS=WARNING`.
- Sem crash; motivo explícito: `offline_ok: network/DNS indisponível no ambiente atual`.

## 9. Estado do Telegram dry-run
- Executado com sucesso.
- Sem token: modo seguro, sem chamadas de rede.
- Lista de comandos e allowed user ids validada.

## 10. Confirmação de segurança
- Real trading bloqueado: **sim**.
- MT5 `order_send` bloqueado: **sim**.
- XTB real bloqueado: **sim**.
- Broker real bloqueado: **sim**.
- LLM sem execução direta: **sim**.
- ATLAS sem execução direta: **sim**.
