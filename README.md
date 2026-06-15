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
