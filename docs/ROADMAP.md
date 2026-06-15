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
