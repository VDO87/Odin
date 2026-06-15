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
- `GET /strategy/status`: estado da estrategia baseline observe-only.
- `GET /decision/intent`: intencao de decisao bloqueada.
- `GET /risk/gate`: gate de risco bloqueante.
- `GET /shadow/proposal`: proposta shadow bloqueada.
- `GET /mt5/bridge`: estado mock-only da futura bridge MT5.
- `GET /mt5/symbols`: mapeamento mock Odin para futura bridge MT5.
- `GET /mt5/feed`: feed mock MT5 com ticks determinísticos e sem ligacao real.
- `GET /runtime/smoke`: validacao local agregada do runtime seguro.

O dashboard e read-only e nao disponibiliza accoes de trading.

## A13 - Runtime Smoke Confirmado

O endpoint `GET /runtime/smoke` faz parte do runtime seguro atual e deve continuar a devolver o estado agregado do smoke local, sem executar subprocessos, ordens ou integracoes reais.

## A14 - MT5 Bridge Mock Endpoint

O endpoint `GET /mt5/bridge` devolve apenas estado mock-only: `bridge_mode=MOCK_ONLY`, `provider=mt5_mock`, `connected=false`, `terminal_detected=false`, `account_connected=false`, `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

## A15 - MT5 Symbol Mapping Mock Endpoint

O endpoint `GET /mt5/symbols` devolve apenas mapeamento mock: 3 simbolos Forex mapeados para equivalentes mock e 6 ativos FIRE mapeados para `non_mt5_fire_asset`, sempre com `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.

## A16 - MT5 Market Feed Mock Endpoint

O endpoint `GET /mt5/feed` devolve apenas feed mock: `feed_mode=MOCK_ONLY`, `provider=mt5_mock`, `source=mt5_mock`, `connected=false`, 3 ticks Forex e flags sempre `execution_allowed=false`, `safe_to_trade=false` e `real_trading=false`.
