# Roadmap

## Estado A13 - Runtime Closeout

- A0 concluida: bootstrap ODIN Hermes Alive architecture.
- A1 concluida: safe core logging bootstrap.
- A2 concluida: dashboard read-only status endpoints.
- A3 concluida: Hermes read-only summary.
- A4 concluida: Treasury PT read-only skeleton.
- A5 concluida: mock market data watchlist.
- A6 concluida: mock market watch mode.
- A7 concluida: data quality gates.
- A8 concluida: baseline strategy observer.
- A9 concluida: decision intent skeleton.
- A10 concluida: risk gate skeleton.
- A11 concluida: shadow proposal skeleton.
- A12 concluida: local runtime smoke pack.
- A13 closeout: documentar `LOCAL_SAFE_RUNTIME` e preparar `v0.1.0-local-safe-runtime`, sem commit/tag automaticos.
- A14 concluida: MT5 Bridge Mock Adapter.
- A15 concluida: MT5 Symbol Mapping Mock.
- A16 concluida: MT5 Market Feed Mock Adapter.
- A17 concluida: MT5 Feed Quality Gate Mock.
- A18 concluida: MT5 Feed Source Selector Mock.
- A19 concluida: Observation Frame Builder Mock.
- A20 concluida: Observation Frame Quality Gate.
- A21 concluida: Strategy Context Snapshot Mock.

## A14 - MT5 Bridge Mock Adapter

- Criar contrato e adaptador mock-only para futura ponte MT5.
- Expor comando `python3 -m odin.cli mt5-bridge`.
- Expor endpoint `GET /mt5/bridge`.
- Integrar o estado mock no smoke local, com `modules_count=11`.
- Manter sem MT5 real, sem login, sem credenciais, sem ordens e sem execucao.

## A15 - MT5 Symbol Mapping Mock

- Criar mapeamento mock Odin -> futura bridge MT5.
- Expor comando `python3 -m odin.cli mt5-symbols`.
- Expor endpoint `GET /mt5/symbols`.
- Mapear 3 simbolos Forex como tradable mock e 6 ativos FIRE como `non_mt5_fire_asset`.
- Integrar o mapeamento no smoke local, com `modules_count=12`.
- Manter sem MT5 real, sem sinais, sem ordens e sem execucao.

## A16 - MT5 Market Feed Mock Adapter

- Criar feed mock usando o mapeamento A15.
- Expor comando `python3 -m odin.cli mt5-feed`.
- Expor endpoint `GET /mt5/feed`.
- Gerar ticks determinísticos apenas para `EURUSD`, `USDJPY` e `GBPUSD`.
- Excluir ativos FIRE do feed MT5 mock.
- Integrar o feed no smoke local, com `modules_count=13`.
- Manter sem MT5 real, sem sinais, sem ordens e sem execucao.

## A17 - MT5 Feed Quality Gate Mock

- Criar gates de qualidade para ticks do feed MT5 mock.
- Expor comando `python3 -m odin.cli mt5-feed-quality`.
- Expor endpoint `GET /mt5/feed/quality`.
- Validar simbolo, bid, ask, spread, timestamp, fonte mock e bloqueio de execucao.
- Integrar a qualidade do feed no smoke local, com `modules_count=14`.
- Manter `safe_to_use_for_decision=false`, sem decisao, sem sinais, sem ordens e sem execucao.

## A18 - Feed Source Selector Mock

- Criar seletor mock entre `market_data_mock` e `mt5_feed_mock`.
- Expor comando `python3 -m odin.cli feed-source`.
- Expor endpoint `GET /feed/source`.
- Preferir `mt5_feed_mock` quando a qualidade A17 esta `OK`.
- Integrar a selecao no smoke local, com `modules_count=15`.
- Manter `safe_to_use_for_decision=false`, sem decisao, sem sinais, sem ordens e sem execucao.

## A19 - Observation Frame Builder Mock

- Criar frame observacional agregado usando feed-source, feed MT5 mock, qualidade, estrategia, intencao, risco e shadow proposal.
- Expor comando `python3 -m odin.cli observation-frame`.
- Expor endpoint `GET /observation/frame`.
- Integrar o frame no smoke local, com `modules_count=16`.
- Manter `safe_to_use_for_decision=false`, sem decisao, sem proposta, sem risco aprovado e sem execucao.

## A20 - Observation Frame Quality Gate

- Validar o frame A19 com gates de qualidade observacionais.
- Expor comando `python3 -m odin.cli observation-frame-quality`.
- Expor endpoint `GET /observation/frame/quality`.
- Integrar os gates no smoke local, com `modules_count=17`.
- Manter `safe_to_use_for_decision=false`, sem decisao, sem proposta, sem risco aprovado e sem execucao.

## A21 - Strategy Context Snapshot Mock

- Criar snapshot imutavel e deterministico a partir da qualidade A20.
- Expor comando `python3 -m odin.cli strategy-context-snapshot`.
- Expor endpoint `GET /strategy/context/snapshot`.
- Integrar o snapshot no smoke local, com `modules_count=18`.
- Manter sem decisao, proposta, risco aprovado, execucao ou trading real.

## A0 - Bootstrap

- Fundacao de pastas.
- Politicas e arquitectura.
- Skills locais.
- Configuracao inicial segura.
- Trading real bloqueado por desenho.

## A1 - Contratos e Logs

- Contratos de eventos.
- Esquema JSONL.
- SQLite local.
- Testes de bloqueios.
- CLI `validate` em OFF_SAFE.
- Risk placeholder `READY_BLOCKING`.
- Hermes `READ_ONLY`.

## A2 - Core Shadow

- Estado operacional.
- Market Watch sem execucao.
- Shadow Decision.
- Dashboard minimo.

## A2 - Dashboard minimo / Estado real

- Dashboard HTTP read-only.
- Endpoints de saude, estado, risco, Hermes e logs.
- Estado obtido atraves dos modulos A1.
- Sem execucao real ou integracoes de broker.

## A3 - Hermes Read-Only

- RAG com fontes auditaveis.
- Memoria read-only.
- Relatorios explicaveis.

## A3 - Hermes Read-Only Summary

- Hermes le estado e logs JSONL.
- Hermes gera resumo e recomendacoes read-only.
- Sem RAG, OpenAI, LLM local ou integracoes externas.
- Sem capacidade de alterar risco, tesouraria, configuracao critica ou execucao.

## Futuro Controlado

Qualquer demo, limited real ou integracao operacional exige revisao formal, testes e aprovacao humana explicita.

## A4 - Treasury PT Skeleton

- Treasury compute-only para Portugal.
- Valores financeiros a zero por defeito.
- Reserva fiscal minima documentada.
- Transferencias bloqueadas por desenho.
- Sem ligacoes a bancos, brokers ou ficheiros fiscais reais.

## A5 - Market Data Mock + Watchlist

- Watchlist mock inicial.
- Snapshot e candles determinísticos para EURUSD.
- Qualidade de dados básica.
- Endpoint de dashboard para estado de mercado mock.
- Sem ligação a MT5 real, APIs financeiras reais ou geração de decisões.

## A6 - Market Watch Mode

- Modo `MARKET_WATCH` com dados mock.
- Observacao e qualidade de dados sem decisao operacional.
- Endpoint de dashboard para o estado de observacao.
- Sem sinais, propostas ou execucao.

## A7 - Data Quality Gates

- Gates bloqueantes para snapshots de mercado mock.
- Relatorio de qualidade com razoes de bloqueio e avisos.
- Integracao informativa com `MARKET_WATCH`.
- Sem decisoes de trading ou execucao.

## A8 - Strategy Baseline Skeleton

- Estrutura base de estrategias observe-only.
- Baseline le estado de qualidade de dados.
- Sem sinais, propostas, dimensionamento ou execucao.
- Endpoint de dashboard para estado da estrategia.

## A9 - Decision Intent Skeleton

- Estrutura futura de intencao de decisao.
- Estado sempre `NO_DECISION` e modo `INTENT_SKELETON`.
- Sem aprovacao de risco, precos operacionais, dimensionamento, propostas ou execucao.
- Endpoint de dashboard para intencao bloqueada.

## A10 - Risk Gate Skeleton

- Gate formal de risco bloqueante.
- Le Decision Intent e devolve `BLOCKED`.
- Sem aprovacao de risco, parametros operacionais ou execucao.
- Endpoint de dashboard para o estado do gate.

## A11 - Shadow Proposal Skeleton

- Estrutura futura de proposta em modo sombra.
- Le Risk Gate e permanece `BLOCKED`.
- Sem direccao de mercado, parametros de ordem, aprovacao de risco ou execucao.
- Endpoint de dashboard para a proposta shadow bloqueada.

## A12 - Local Runtime Smoke Pack

- Validacao local agregada dos modulos principais.
- Comando unico para confirmar estado seguro e bloqueante.
- Sem comandos shell internos, sem execucao e sem novas integracoes.
- Endpoint de dashboard para resultado do smoke.

## A22 - Strategy Context Snapshot Quality Gate

- Adds a read-only quality gate over A21 snapshot consistency.
- Validates mode, version, required schema fields, deterministic fingerprint and fail-closed flags.
- Does not authorize decisions, proposals, risk approval, execution or real trading.
