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
  stale; `terminal_trade_allowed=true`, `account_trade_allowed=true` e
  `account_trade_expert=true`; zero posições e zero ordens. A permissão foi
  observada, não alterada automaticamente pelo ODIN.
- Trades autónomos RC2 completos: 0.
- Soak de mercado aberto acumulado: 0 horas.
- Resource guardian: ativo; GPU/VRAM, CPU/RAM, disco, WSL, FD/handles,
  processos, logs/SQLite e Hermes/Ollama visíveis no Cockpit. O firmware não
  expõe temperatura CPU; esta ausência aparece como warning explícito. GPU foi
  observada a 38–39 °C, abaixo do limite de 80 °C.
- O resource probe Windows foi separado do subprobe WSL bounded de 10 s depois
  de bloqueios transitórios observados. Cinco ciclos reais consecutivos passaram
  sem BLOCK, com uma única instância e zero exposição.
- Hermes-versus-Reality está ativo e read-only. A prova mais recente foi
  `ANALYZED/SCORED`; o histórico preserva quatro claims `CONFIRMED` e quatro
  `CONTRADICTED`, sem apagar alucinações anteriores.
- O incident ledger sofreu um reset acidental documentado, foi reconstruído com
  marcadores de recuperação e voltou a receber append normal. A linha pós-reset
  original permanece guardada com hash no dossier de recovery.
- Acceptance RC2: `NOT_READY` até 24 horas de mercado aberto e pelo menos cinco
  trades autónomos completos/reconciliados, além da suite final e recovery.
- O audit trail histórico do dashboard foi verificado (`SQLite quick_check=ok`)
  e arquivado em `D:\ODIN_LOCAL\archives\dashboard-audit-20260829T2325Z`.
  Cockpit, overview e healthcheck passaram a ler snapshots persistentes sem
  reconstruir pipelines; o overview live caiu de 11,955 s para 0,186 s.

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
- `d2cb9c7` — probe local verificado e primeira estabilização WSL.
- `9195ab7` — contenção bounded da disputa de startup.
- `6492e59` — análise Hermes-versus-Reality bounded.
- `6d7d7ba` — output Hermes limitado e normalização de tipos.
- `6dc91a9` — subprobe WSL isolado com timeout de 10 s.
- `4a202de` — rejeição fail-closed de placeholders do modelo.
- `06d4023` — contrato Hermes reduzido a uma claim factual por trigger.
- `7fa5ccd` — uptime, ciclo, próximo check, branch/checkpoint e último repair
  visíveis no painel Supervisor do TradeDesk.
- `8e29e0b` — repairs completos e auto-restart do dashboard auditável.
- `8687728` — anotação append-only e relatório deduplicado por fingerprint.
- `2a93d4e` — regressões posteriores a um fix classificadas como `REGRESSION`.
- `3c7dfdc` — curva MT5 DEMO reconciliada e bounded no TradeDesk; recovery
  autónomo do dashboard comprovado em 34,8 s.
- `4bce696` — timeline real e redigida do Execution Ledger na Visão Geral.
- `de289fd` — paths SVG válidos para a curva financeira MT5 DEMO.
- `d02af7b` — publicação dos relatórios tolera contenção Windows bounded.
- `06166ab` — terminal MetaQuotes-Demo retirado do caminho ativo de observação.
- `c455828` — writers SQLite do dashboard serializados e WAL ativado.
- `7178dd6` — Cockpit deixou de fazer polling recursivo do overview.
- `28e3ffd` — overview passou a projetar apenas estado persistente RC2.
- `25fb4e1` — healthcheck tornou-se puro e sem reconstrução do runtime.

## Próximos gates

1. Preservar a permissão Algo Trading já observada; o ODIN não a altera.
2. Aguardar sessão EURUSD elegível com ticks FRESH e spread dentro do limite.
3. Supervisor observa decisões legítimas sem forçar sinal.
4. Cada trade passa Strategy → Risk → Demo Gate → broker → ledgers → reconciliação.
5. Acumular 24h de mercado aberto e pelo menos cinco trades autónomos completos.
6. A suite integral pré-soak mais recente teve `853 passed`, `42 subtests`,
   duração 623,89 s e FD soft limit 8192; repetir a suite integral no checkpoint
   final após o soak.

`safe_to_trade=false`  
`real_trading=false`  
`execution_allowed=false`
