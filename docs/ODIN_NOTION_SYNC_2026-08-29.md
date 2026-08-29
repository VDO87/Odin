# ODIN Notion Sync — 2026-08-29

Documento factual para atualização manual do Notion. Quando houver divergência,
MT5, histórico do broker e ledgers locais prevalecem.

## Estado real

- Branch ativa: `feature/autonomous-demo-operations-rc2`.
- Primeiro canary: `COMPLETE_AND_RECONCILED`, fecho por SL, P/L realizado
  `-0.88 EUR`.
- Supervisor RC2: persistente via Windows Task Scheduler, ação direta do Python
  base, single-instance, heartbeat e estado durável. `Stop-ScheduledTask` foi
  comprovado com zero processos residuais e restart com uma instância.
- TradeDesk: `http://127.0.0.1:8765/`.
- Cockpit: `http://127.0.0.1:8765/cockpit`.
- Broker: OANDA TMS Brokers S.A.; server `OANDATMS-MT5`; conta comprovadamente
  DEMO; símbolo lógico `EURUSD`, símbolo broker `EURUSD.pro`.
- Terminal autorizado: `C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe`.
- Terminal MetaQuotes-Demo em `D:\ODIN_LOCAL\mt5\terminal64.exe`: excluído do
  caminho ativo e de qualquer fallback.
- Estado de mercado na atualização: `WAITING_MARKET`; tick de fim de semana
  stale; `terminal_trade_allowed=false`; zero posições e zero ordens.
- Trades autónomos RC2 completos: 0.
- Soak de mercado aberto acumulado: 0 horas.
- Resource guardian: ativo; GPU/VRAM, CPU/RAM, disco, WSL, FD/handles,
  processos, logs/SQLite e Hermes/Ollama visíveis no Cockpit. O firmware não
  expõe temperatura CPU; esta ausência aparece como warning explícito. GPU foi
  observada a 38–39 °C, abaixo do limite de 80 °C.
- Acceptance RC2: `NOT_READY` até 24 horas de mercado aberto e pelo menos cinco
  trades autónomos completos/reconciliados, além da suite final e recovery.

## Componentes consolidados

- Risk Engine determinístico é o agente de risco independente.
- Demo Execution Gate + adapter MT5 são a execução determinística única.
- Data Quality/market time concentram freshness, timestamps, spread e identidade.
- Daily Supervisor/Weekly Gate cobrem auditoria; não criar outro daemon auditor.
- Incident memory JSONL mantém fingerprints e reparações sem credenciais.
- Hermes-versus-Reality usa claims estruturados, classificação factual e não tem
  autoridade financeira.

## Decisões de arquitetura

- `N8N_DECISION=NOT_NEEDED`.
- Agent Zero: `DEFERRED — NOT IN ACTIVE RUNTIME`.
- Oh My Hermes: `DEFERRED — NOT IN ACTIVE RUNTIME`.
- Aprendizagem: `DATA COLLECTION ONLY`; sem promoção online de estratégia.
- Nenhum componente histórico, ledger, relatório ou dataset foi apagado.

## Checkpoints RC2

- `0934b45` — fundação supervisor/estado/gate RC2.
- `f45c9df` — handoff persistente e Task Scheduler.
- `59c384a` — ciclo financeiro e lifecycle reconciliation.
- `ce9aa39` — dashboard financeiro live.
- `ec6f03f` — relatórios operacionais duráveis.
- `0d1742e` — racionalização e runbook.
- `ae5be45` — controlos imediatos e deduplicação de incidentes.
- `a97150c` — recovery e Hermes-versus-Reality no dashboard.
- `e14c07b` — isolamento dos smokes e sentinelas do dashboard.
- `1e945c3` — correção da race de sleep bounded.
- `c422557` — resource guardian fail-closed.
- `bf14f19` — processo direto controlado pelo Task Scheduler.
- `cf5112c` — observabilidade financeira live completa.

## Próximos gates

1. Operador ativa manualmente Algo Trading no terminal DEMO autorizado.
2. Mercado EURUSD abre com ticks FRESH e spread dentro do limite.
3. Supervisor observa decisões legítimas sem forçar sinal.
4. Cada trade passa Strategy → Risk → Demo Gate → broker → ledgers → reconciliação.
5. Acumular 24h de mercado aberto e pelo menos cinco trades autónomos completos.
6. A última suite integral verde antes das extensões finais teve `833 passed` e
   `42 subtests`; repetir a suite integral no checkpoint final após o soak.

`safe_to_trade=false`  
`real_trading=false`  
`execution_allowed=false`
