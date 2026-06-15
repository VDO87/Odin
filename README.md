# ODIN_HERMES_ALIVE

Fundacao limpa para a fase A0 - Bootstrap.

ODIN e o motor operacional: core, risco, dados, logs, tesouraria e execucao controlada. Hermes e a camada cognitiva: memoria, RAG, relatorios, recomendacoes e apoio ao operador. O Dashboard e o cockpit humano para auditoria, logs e decisao assistida.

Estado inicial:

- Trading real bloqueado por defeito.
- Hermes em modo read-only.
- MT5 limitado a Market Watch, Shadow Decision e Demo futura.
- XTB limitado a operacao manual/assistida, sem cliques automaticos.
- Codex limitado a engenharia interna em staging/desenvolvimento.

Este projecto ainda nao implementa logica funcional de trading.

## Current Safe Runtime

Estado atual: `LOCAL_SAFE_RUNTIME`, preparado para a release `v0.1.0-local-safe-runtime`.

Comando principal de validacao:

```bash
python3 -m odin.cli smoke
```

Dashboard smoke:

- `GET /runtime/smoke`

Garantias principais: `safe_to_trade=false`, `real_trading=false`, `execution_allowed=false`, Hermes `READ_ONLY`, Treasury `READ_ONLY`, Risk Gate `BLOCKED` e Shadow Proposal `BLOCKED`.

## Validacao rapida

```bash
find ODIN_HERMES_ALIVE -maxdepth 4 -type f | sort
python3 -m tomllib ODIN_HERMES_ALIVE/pyproject.toml
```

## A1 - Validacao Segura

```bash
python -m odin.cli validate
```

Resultado esperado: `status=PASS`, `mode=OFF_SAFE`, `safe_to_trade=false`, `real_trading=false`, Risk em `READY_BLOCKING` e Hermes em `READ_ONLY`.

## A2 - Dashboard Read-Only

```bash
python3 -m odin.cli dashboard --host 127.0.0.1 --port 8765
```

Endpoints:

- `GET /health`
- `GET /state`
- `GET /risk/status`
- `GET /hermes/status`
- `GET /logs/tail`

O dashboard nao executa ordens, nao desbloqueia trading e apenas mostra estado seguro.

## A3 - Hermes Read-Only Summary

```bash
python3 -m odin.cli hermes-summary
```

O resumo Hermes le o estado seguro e os logs JSONL, devolve `read_only=true` e apenas gera recomendacoes sujeitas a revisao humana.

Endpoint:

- `GET /hermes/summary`

## A4 - Treasury PT Skeleton

```bash
python3 -m odin.cli treasury-status
```

O Treasury A4 e read-only/compute-only, usa valores zero por defeito, nao liga a bancos ou brokers e devolve `safe_to_transfer=false`.

Endpoint:

- `GET /treasury/status`

## A5 - Market Data Mock

```bash
python3 -m odin.cli market-status
```

A camada A5 usa apenas dados determinísticos mock, e declara `read_only=true`, `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

Endpoint:

- `GET /market/status`

## A6 - Market Watch Mock

```bash
python3 -m odin.cli market-watch
```

O modo `MARKET_WATCH` observa dados mock, valida qualidade e mantem `safe_to_trade=false`, `real_trading=false` e `execution_allowed=false`.

Endpoint:

- `GET /market/watch`

## A7 - Data Quality Gates

```bash
python3 -m odin.cli data-quality
```

Os gates validam snapshots mock antes de qualquer fase futura de decisao. Mesmo quando o estado e `OK`, `safe_to_use_for_decision=false`, `safe_to_trade=false`, `real_trading=false` e `execution_allowed=false`.

Endpoint:

- `GET /data/quality`

## A8 - Strategy Baseline Skeleton

```bash
python3 -m odin.cli strategy-status
```

A estrategia baseline e apenas observacional: le qualidade de dados mock e devolve `READY_NO_DECISION`, mantendo `decision_generated=false`, `trade_proposal_generated=false`, `safe_to_trade=false`, `real_trading=false` e `execution_allowed=false`.

Endpoint:

- `GET /strategy/status`

## A9 - Decision Intent Skeleton

```bash
python3 -m odin.cli decision-intent
```

A intencao de decisao A9 e apenas uma estrutura bloqueada: le a estrategia baseline e devolve `NO_DECISION`, `INTENT_SKELETON`, `risk_approved=false`, `decision_generated=false`, `trade_proposal_generated=false`, `safe_to_trade=false`, `real_trading=false` e `execution_allowed=false`.

Endpoint:

- `GET /decision/intent`

## A10 - Risk Gate Skeleton

```bash
python3 -m odin.cli risk-gate
```

O Risk Gate A10 le a intencao de decisao e bloqueia tudo por defeito: devolve `risk_status=BLOCKED`, `risk_gate_mode=BLOCKING_SKELETON`, `risk_approved=false`, `safe_to_trade=false`, `real_trading=false` e `execution_allowed=false`.

Endpoint:

- `GET /risk/gate`

## A11 - Shadow Proposal Skeleton

```bash
python3 -m odin.cli shadow-proposal
```

A Shadow Proposal A11 le o Risk Gate e permanece bloqueada: devolve `shadow_proposal_status=BLOCKED`, `shadow_mode=SHADOW_SKELETON`, `shadow_only=true`, `risk_status=BLOCKED`, `risk_approved=false`, `safe_to_trade=false`, `real_trading=false` e `execution_allowed=false`.

Endpoint:

- `GET /shadow/proposal`

## A12 - Local Runtime Smoke Pack

```bash
python3 -m odin.cli smoke
```

O Smoke Pack A12 valida localmente os modulos principais do Odin num unico comando, chamando funcoes Python internas. O resultado esperado e `status=PASS`, `smoke_mode=LOCAL_SAFE_SMOKE`, `all_modules_ok=true`, `safe_state_confirmed=true`, `blocking_state_confirmed=true`, `safe_to_trade=false`, `real_trading=false` e `execution_allowed=false`.

Endpoint:

- `GET /runtime/smoke`

## A14 - MT5 Bridge Mock Adapter

```bash
python3 -m odin.cli mt5-bridge
```

A bridge MT5 A14 e apenas mock: devolve `bridge_mode=MOCK_ONLY`, `provider=mt5_mock`, `connected=false`, `terminal_detected=false`, `account_connected=false`, `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

Endpoint:

- `GET /mt5/bridge`

## A15 - MT5 Symbol Mapping Mock

```bash
python3 -m odin.cli mt5-symbols
```

O mapeamento A15 e apenas mock: mapeia Forex para simbolos mock equivalentes e marca ativos FIRE como `non_mt5_fire_asset`, mantendo `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

Endpoint:

- `GET /mt5/symbols`

## A16 - MT5 Market Feed Mock Adapter

```bash
python3 -m odin.cli mt5-feed
```

O feed A16 e apenas mock: usa o mapeamento A15 para expor ticks determinísticos de `EURUSD`, `USDJPY` e `GBPUSD`, exclui ativos FIRE e mantem `connected=false`, `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

Endpoint:

- `GET /mt5/feed`

## A17 - MT5 Feed Quality Gate Mock

```bash
python3 -m odin.cli mt5-feed-quality
```

Os gates A17 validam os ticks mock do feed MT5 antes de qualquer uso futuro em decisao. O resultado esperado e `quality_mode=MOCK_FEED_GATES`, `all_ticks_valid=true`, `safe_to_use_for_decision=false`, `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

Endpoint:

- `GET /mt5/feed/quality`

## A18 - Feed Source Selector Mock

```bash
python3 -m odin.cli feed-source
```

O seletor A18 escolhe apenas a fonte observacional mock preferida: `selected_source=mt5_feed_mock`, com fallback `market_data_mock`. A selecao continua bloqueada para decisao e execucao: `safe_to_use_for_decision=false`, `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

Endpoint:

- `GET /feed/source`

## A19 - Observation Frame Builder Mock

```bash
python3 -m odin.cli observation-frame
```

O frame A19 agrega estado observacional de fonte, feed MT5 mock, qualidade, estrategia, intencao, risco e shadow proposal. O frame e `OBSERVATION_ONLY` e mantem `safe_to_use_for_decision=false`, `decision_generated=false`, `trade_proposal_generated=false`, `risk_approved=false`, `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

Endpoint:

- `GET /observation/frame`
