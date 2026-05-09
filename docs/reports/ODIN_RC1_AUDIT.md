# ODIN RC1 Audit

Date: 2026-05-09
Scope: local workspace snapshot only.

## 1) Estrutura actual de pastas
- Projeto já contém estrutura madura em `src/` (`core`, `dash`, `risk`, `exec`, `market`, `recovery`, `operator_console`, `shared`, etc).
- Também existem `docs/`, `tests/`, `config/examples`, `runtime/`, scripts de instalação/start.

## 2) Ficheiros principais existentes
- `README.md`
- `pyproject.toml`
- `start_odin.sh`
- `INSTALL_ODIN.sh`
- `src/apps/core_service.py`
- `src/apps/core_daemon.py`
- `src/apps/operator_console.py`
- `src/operator_console/server.py`

## 3) Testes existentes
- Unit, integration, contract, replay, scenarios.
- Exemplos: `tests/unit/test_state_machine.py`, `tests/integration/test_operator_console_flow.py`, `tests/contract/test_real_exec_adapter_contracts.py`.

## 4) Comandos disponíveis
- Entrypoints no `pyproject.toml`:
  - `odin-core`
  - `odin-core-daemon`
  - `odin-validate-config`
  - `odin-operator-console`
- Scripts locais:
  - `start_odin.sh`
  - `INSTALL_ODIN.sh`

## 5) Estado do Operator Console / Dashboard
- Existe dashboard web local em `src/operator_console/web/`.
- API servida por `src/operator_console/server.py`.
- Comandos principais disponíveis no gateway: `status`, `pause`, `resume`, `stop`, `export-logs`, `get-config`, `validate-config`.

## 6) Estado do Risk Engine
- Implementado no domínio actual (`src/risk/domain.py`) com decisões `ALLOW/RESTRICT/BLOCK/KILL`.
- Integrado no runtime (`src/core/runtime.py`).

## 7) Estado de MT5
- Não foi identificado adapter MT5 operacional completo neste corte.
- Há contratos/planeamento e referências de routing/advisory.

## 8) Estado de XTB
- Não foi identificado adapter XTB operacional completo neste corte.
- Existe posicionamento de workflow assisted/advisory em docs e UI.

## 9) Estado de Telegram
- Não existe bot Telegram operacional pronto neste snapshot.
- Há contratos e planeamento para bridge/gateway.

## 10) Estado de LLM local
- Existe provider `AnythingLLM` (`src/intelligence/providers/anythingllm.py`), mas não como assistente operacional RC1 completo.

## 11) Estado de OpenAI support
- Existem contratos/referências para advisory OpenAI, sem ativação operacional por defeito.

## 12) Estado dos logs
- Runtime já grava logs JSONL em `runtime/logs`.
- Falta estrutura RC1 dedicada por domínio (`logs/assistant`, `logs/atlas`, `logs/brokers`, etc).

## 13) Estado do healthcheck
- Há métricas de liveness/heartbeat no runtime actual.
- Healthcheck RC1 unificado (rede/dns/disco/config/llm/telegram/apis) ainda não está consolidado em módulo próprio.

## 14) O que existe
- Núcleo de estado/eventos, risk, recovery, dashboard, persistência e testes robustos já existe.

## 15) O que falta
- Estrutura RC1 explícita pedida (novos módulos `odin_*`, assistant unificado dashboard+telegram, ATLAS, broker router comum, mt5 shadow reconciler, healthcheck dedicado, logs RC1 por domínio).

## 16) Prioridades para fechar RC1
1. Criar camada `odin_control` com command bus, state machine e recovery/network gating.
2. Criar `odin_health` consolidado com status `OK/WARNING/CRITICAL/BLOCKED`.
3. Criar `odin_execution` shadow MT5 + reconciliação + bloqueio automático.
4. Criar `odin_assistant` com question registry e integrações seguras.
5. Criar `odin_atlas` (consensus-only, sem execução).
6. Criar `odin_brokers` com interface única e `place_order` bloqueado por default.
7. Criar dashboard HTML/terminal/telegram RC1 ligados ao Command Bus.
