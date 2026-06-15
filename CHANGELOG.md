# Changelog

## 0.0.0 - A0 Bootstrap

- Criada a fundacao documental do projecto.
- Criadas as politicas de arquitectura, risco, tesouraria, RAG, Hermes, Codex, Dashboard, MT5 e XTB.
- Criadas skills locais para orientar trabalho futuro do Codex.
- Criadas configuracoes iniciais com trading real bloqueado por defeito.

## A1 - Core Vivo + Logging Base

- Adicionado estado OFF_SAFE com `safe_to_trade=false` e `real_trading=false`.
- Adicionado Risk Engine placeholder em `READY_BLOCKING`.
- Adicionadas permissoes Hermes em `READ_ONLY`.
- Adicionados logger JSONL, SQLite local e comando `python -m odin.cli validate`.
- Adicionados testes A1 para estado seguro, logging, SQLite e ausencia de referencias de execucao real em `src/odin`.

## A2 - Dashboard minimo / Estado real

- Adicionado dashboard HTTP read-only com biblioteca standard.
- Adicionados endpoints `/health`, `/state`, `/risk/status`, `/hermes/status` e `/logs/tail`.
- O dashboard obtem estado atraves do runtime A1 e preserva `OFF_SAFE`.
- Adicionados testes A2 para endpoints, estado seguro e ausencia de referencias de execucao real.

## A3 - Hermes Read-Only Summary

- Adicionado Hermes como leitor/relator read-only.
- Adicionado comando `python3 -m odin.cli hermes-summary`.
- Adicionado endpoint `/hermes/summary` no dashboard.
- Adicionadas recomendacoes read-only sem capacidade de execucao.
