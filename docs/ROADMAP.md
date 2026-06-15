# Roadmap

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
