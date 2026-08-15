# Dashboard Spec

O Dashboard e o cockpit humano para auditoria, logs e decisao assistida.

Vistas iniciais previstas:

- Estado do Core.
- Estado do Risk.
- Estado do Treasury.
- Estado de Hermes.
- Logs JSONL.
- Relatorios.
- Shadow Decision.
- Alertas e bloqueios.

Regra critica:

O Dashboard nunca pode mostrar "pronto para real" se Core ou Risk estiver bloqueado.

## A2 - Endpoints Minimos

- `GET /health`: saude do dashboard e flags seguras.
- `GET /state`: estado real validado pelo runtime A1.
- `GET /risk/status`: Risk em `READY_BLOCKING`.
- `GET /hermes/status`: Hermes em `READ_ONLY`.
- `GET /logs/tail`: ultimos eventos JSONL.
- `GET /hermes/summary`: resumo Hermes read-only.
- `GET /treasury/status`: estado Treasury PT read-only.
- `GET /market/status`: estado de dados de mercado mock.
- `GET /market/watch`: modo MARKET_WATCH observacional.
- `GET /data/quality`: gates de qualidade de dados.
- `GET /data/history/canonical`: estado do último manifesto de candles históricos
  validado, ou bloqueio explícito se não existir dataset válido.
- `GET /feed/source`: selecao mock de fonte observacional.
- `GET /observation/frame`: frame observacional agregado.
- `GET /observation/frame/quality`: gates de qualidade do frame observacional.
- `GET /strategy/status`: estado da estrategia baseline observe-only.
- `GET /decision/intent`: intencao de decisao bloqueada.
- `GET /risk/gate`: gate de risco bloqueante.
- `GET /shadow/proposal`: proposta shadow bloqueada.
- `GET /mt5/demo/session`: estado persistido da preparacao DEMO, sem login ou contacto ao terminal.
- `GET /mt5/bridge`: estado mock-only da futura bridge MT5.
- `GET /mt5/symbols`: mapeamento mock Odin para futura bridge MT5.
- `GET /mt5/feed`: feed mock MT5 com ticks determinísticos e sem ligacao real.
- `GET /mt5/feed/quality`: gates de qualidade do feed MT5 mock.
- `GET /runtime/smoke`: validacao local agregada do runtime seguro.

O dashboard e read-only e nao disponibiliza accoes de trading.

## TradeDesk DEMO

`/` is the local TradeDesk for simulated account, replay P/L, open and closed replay operations, decision journal, data provenance and constrained replay preferences. When the bounded DEMO collector has a fresh local state, it also shows the MT5 DEMO account summary, open positions and EURUSD M15 observation separately from replay. The DEMO collection audit is `D:\ODIN_LOCAL\logs\mt5_demo_readonly.jsonl`; it contains timestamp, status, candle count and content hash, never credentials. `/cockpit` remains the technical read-only view for ODIN, Hermes, resources and events. The only configuration endpoint is local `POST /trading/replay/config`; it persists an allowlisted replay watchlist and bounded simulated risk limits, and always returns `execution_allowed=false`, `safe_to_trade=false` and `real_trading=false`.

## Operational reports

`python3 -m odin.cli operational-report` persists a metadata-only report by default under `D:\ODIN_LOCAL\reports` (WSL: `/mnt/d/ODIN_LOCAL/reports`). It is read-only and contains no credentials or remote response content.

## Bounded manual observation refresh

`scripts/windows/Refresh-ODIN-Observations.ps1` is the operator-run refresh path. It first collects the already-authorized MT5 DEMO state in read-only mode, then refreshes the bounded ECB observation and writes an operational report. Every stage has a timeout and failure stops later stages. It does not run continuously, send orders, generate a trading decision or modify execution flags.

The Windows installer creates `ODIN TradeDesk (Demo).lnk` and `ODIN Refresh DEMO Observations.lnk` on the Desktop. The latter is a manual read-only collection action and contains no credentials.

The complete operator walkthrough is [OPERATOR_DEMO_WALKTHROUGH.md](OPERATOR_DEMO_WALKTHROUGH.md).

## Histórico canónico de candles

O TradeDesk consulta `GET /data/history/canonical` e mostra apenas a metadata de
um manifesto `VALIDATED`: fonte, período, proveniência, qualidade e hash. Não
mostra recomendações. O carregamento é feito localmente com
`python3 -m odin.cli historical-candles-import --csv <ficheiro> --symbol EURUSD --timeframe M15`;
o importador conserva `execution_allowed=false` e rejeita falhas em vez de as
corrigir. O contrato completo está em [CANONICAL_HISTORICAL_CANDLES_CSV.md](CANONICAL_HISTORICAL_CANDLES_CSV.md).

## A13 - Runtime Smoke Confirmado

O endpoint `GET /runtime/smoke` faz parte do runtime seguro atual e deve continuar a devolver o estado agregado do smoke local, sem executar subprocessos, ordens ou integracoes reais.

## A14 - MT5 Bridge Mock Endpoint

O endpoint `GET /mt5/bridge` devolve apenas estado mock-only: `bridge_mode=MOCK_ONLY`, `provider=mt5_mock`, `connected=false`, `terminal_detected=false`, `account_connected=false`, `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

## A15 - MT5 Symbol Mapping Mock Endpoint

O endpoint `GET /mt5/symbols` devolve apenas mapeamento mock: 3 simbolos Forex mapeados para equivalentes mock e 6 ativos FIRE mapeados para `non_mt5_fire_asset`, sempre com `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

## A16 - MT5 Market Feed Mock Endpoint

O endpoint `GET /mt5/feed` devolve apenas feed mock: `feed_mode=MOCK_ONLY`, `provider=mt5_mock`, `source=mt5_mock`, `connected=false`, 3 ticks Forex e flags sempre `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

## A17 - MT5 Feed Quality Mock Endpoint

O endpoint `GET /mt5/feed/quality` devolve apenas gates de qualidade do feed mock: `quality_mode=MOCK_FEED_GATES`, `symbols_checked=3`, `all_ticks_valid=true`, `safe_to_use_for_decision=false`, `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

## A18 - Feed Source Selector Mock Endpoint

O endpoint `GET /feed/source` devolve apenas selecao mock de fonte observacional: `selector_mode=MOCK_ONLY`, `selected_source=mt5_feed_mock`, `fallback_source=market_data_mock`, `safe_to_use_for_decision=false`, `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

## A19 - Observation Frame Mock Endpoint

O endpoint `GET /observation/frame` devolve apenas frame agregado `OBSERVATION_ONLY`: fonte selecionada, simbolo primario, qualidade, estrategia, intencao, risco e shadow proposal, sempre com decisao, proposta, risco aprovado e execucao bloqueados.

## A20 - Observation Frame Quality Endpoint

O endpoint `GET /observation/frame/quality` devolve apenas gates de qualidade para o frame A19: `quality_mode=OBSERVATION_FRAME_GATES`, `frame_quality_status=OK`, `all_gates_passed=true`, com decisao, proposta, risco aprovado e execucao bloqueados.

## A21 - Strategy Context Snapshot Endpoint

O endpoint `GET /strategy/context/snapshot` devolve um snapshot `MOCK_OBSERVATION_ONLY`, imutavel e deterministico, com fingerprint observacional e todos os flags de decisao, proposta, risco aprovado, execucao e trading real bloqueados.

## A22 Strategy Context Snapshot Quality

- Endpoint: `/strategy/context/snapshot/quality`.
- Returns the immutable A22 quality report as JSON.
- Read-only and fail-closed; all critical trading and execution flags remain `false`.
