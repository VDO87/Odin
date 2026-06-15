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

O dashboard e read-only e nao disponibiliza accoes de trading.
