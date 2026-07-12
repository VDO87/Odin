# Changelog

## Unreleased - Fase 6 Ensaio Controlado

- Adicionado fluxo isolado entre proposta Ollama, validadores e revisao Codex.
- Limitada a aplicacao de propostas a sandboxes descartaveis e caminhos autorizados.
- Fixados os validadores em pytest, Ruff e mypy, sem aceitar comandos do modelo.
- Adicionada repeticao local delimitada e escalamento persistente sem chamada automatica.
- Impedido o estado COMPLETED automatico; sucesso tecnico aguarda aprovacao.
- Adicionados timeout por operacao, limite global e watchdog externo apos deteccao de bloqueio.
- Validado escalamento real para CODEX_REVIEW perante erro repetido do modelo local.

## Unreleased - Fase 5 Motor de Progresso e Escalamento

- Adicionada maquina de estados persistente para tarefas Hermes.
- Adicionada avaliacao objectiva por testes, cobertura, lint, tipagem, ambito e regressao.
- Limitadas as tentativas locais e criado escalamento por ausencia de progresso.
- Adicionado pacote compacto de diagnostico para revisao Codex.
- Mantidas desactivadas chamadas automaticas ao Codex e aplicacao automatica de codigo.

## Unreleased - Fase 4 Hermes Ollama Adapter

- Adicionado adaptador local controlado entre Hermes e Ollama.
- Limitados endpoint, contexto, temperatura, tentativas, timeout e duracao por tarefa.
- Adicionados cancelamento, validacao de resposta e resultado estruturado com metricas.
- Adicionado log de auditoria sem prompts, respostas ou segredos.
- Mantidas bloqueadas execucao, alteracao do repositorio e capacidades de trading.
- Validada inferencia real com `qwen2.5-coder:1.5b` na Quadro M4000.

## Unreleased - A19 Observation Frame Builder Mock

- Adicionado contrato de frame observacional agregado.
- Adicionado comando `python3 -m odin.cli observation-frame`.
- Adicionado endpoint read-only `GET /observation/frame`.
- Integrado `observation-frame` no smoke local, elevando o total para 16 modulos seguros.

## Unreleased - A18 Feed Source Selector Mock

- Adicionado contrato de selecao mock de fonte observacional.
- Adicionado comando `python3 -m odin.cli feed-source`.
- Adicionado endpoint read-only `GET /feed/source`.
- Integrado `feed-source` no smoke local, elevando o total para 15 modulos seguros.

## Unreleased - A17 MT5 Feed Quality Gate Mock

- Adicionado contrato de qualidade do feed mock MT5 com gates por tick.
- Adicionado comando `python3 -m odin.cli mt5-feed-quality`.
- Adicionado endpoint read-only `GET /mt5/feed/quality`.
- Integrado `mt5-feed-quality` no smoke local, elevando o total para 14 modulos seguros.

## Unreleased - A16 MT5 Market Feed Mock Adapter

- Adicionado contrato de feed mock MT5 com ticks determinísticos para `EURUSD`, `USDJPY` e `GBPUSD`.
- Adicionado comando `python3 -m odin.cli mt5-feed`.
- Adicionado endpoint read-only `GET /mt5/feed`.
- Integrado `mt5-feed` no smoke local, elevando o total para 13 modulos seguros.

## Unreleased - A15 MT5 Symbol Mapping Mock

- Adicionado contrato de mapeamento mock de simbolos Odin para futura bridge MT5.
- Adicionado comando `python3 -m odin.cli mt5-symbols`.
- Adicionado endpoint read-only `GET /mt5/symbols`.
- Integrado `mt5-symbols` no smoke local, elevando o total para 12 modulos seguros.

## Unreleased - A14 MT5 Bridge Mock Adapter

- Adicionado contrato `MT5BridgeStatus` para estado mock-only da futura bridge MT5.
- Adicionado comando `python3 -m odin.cli mt5-bridge`.
- Adicionado endpoint read-only `GET /mt5/bridge`.
- Integrado `mt5-bridge` no smoke local, mantendo runtime bloqueado e sem integracao real.

## Unreleased - A13 Runtime Closeout

- Adicionado closeout documental da base `LOCAL_SAFE_RUNTIME`.
- Preparada a release candidate documental `v0.1.0-local-safe-runtime`.
- Adicionado runbook de handoff do runtime local seguro.
- Confirmada a cadeia segura A0-A12 sem novas capacidades operacionais.

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

## A4 - Treasury PT skeleton

- Adicionado Treasury Engine compute-only para Portugal.
- Adicionado comando `python3 -m odin.cli treasury-status`.
- Adicionado endpoint `/treasury/status` no dashboard.
- Todas as transferencias ficam bloqueadas por desenho e os valores financeiros arrancam a zero.

## A5 - Market Data Mock + Watchlist

- Adicionada camada de dados de mercado mock/read-only.
- Adicionado comando `python3 -m odin.cli market-status`.
- Adicionado endpoint `/market/status` no dashboard.
- Adicionada watchlist mock com Forex e FIRE documental, sem dados reais ou execucao.

## A6 - Market Watch Mode mock

- Adicionado modo `MARKET_WATCH` observacional com dados mock.
- Adicionado comando `python3 -m odin.cli market-watch`.
- Adicionado endpoint `/market/watch` no dashboard.
- O modo nao gera decisoes, propostas ou execucao.

## A7 - Data Quality Gates

- Adicionados gates bloqueantes de qualidade de dados para snapshots mock.
- Adicionado comando `python3 -m odin.cli data-quality`.
- Adicionado endpoint `/data/quality` no dashboard.
- Market Watch passa a expor estado de qualidade sem permitir decisoes ou execucao.

## A8 - Strategy Baseline Skeleton

- Adicionada estrutura base de estrategias observe-only.
- Adicionado comando `python3 -m odin.cli strategy-status`.
- Adicionado endpoint `/strategy/status` no dashboard.
- A estrategia baseline le qualidade de dados, mas nao gera sinais, propostas ou execucao.

## A9 - Decision Intent Skeleton

- Adicionado esqueleto de intencao de decisao sempre bloqueado.
- Adicionado comando `python3 -m odin.cli decision-intent`.
- Adicionado endpoint `/decision/intent` no dashboard.
- A intencao le o estado da estrategia, mas nao aprova risco, nao gera propostas e nao executa.

## A10 - Risk Gate Skeleton

- Adicionado Risk Gate formal sempre bloqueante.
- Adicionado comando `python3 -m odin.cli risk-gate`.
- Adicionado endpoint `/risk/gate` no dashboard.
- O gate le Decision Intent, mas mantem `risk_status=BLOCKED` e `risk_approved=false`.

## A11 - Shadow Proposal Skeleton

- Adicionada Shadow Proposal sempre bloqueada.
- Adicionado comando `python3 -m odin.cli shadow-proposal`.
- Adicionado endpoint `/shadow/proposal` no dashboard.
- A proposta shadow le Risk Gate, mas nao cria direccao de mercado, parametros ou execucao.

## A12 - Local Runtime Smoke Pack

- Adicionado Smoke Pack local para validar os modulos principais num unico comando.
- Adicionado comando `python3 -m odin.cli smoke`.
- Adicionado endpoint `/runtime/smoke` no dashboard.
- O smoke chama funcoes Python internas e confirma estado seguro, bloqueante e sem execucao.

## A20 - Observation Frame Quality Gate

- Adicionados gates de qualidade para validar o Observation Frame A19.
- Adicionado comando `python3 -m odin.cli observation-frame-quality`.
- Adicionado endpoint `/observation/frame/quality` no dashboard.
- Smoke Pack passa a incluir `observation-frame-quality`, com `modules_count=17`.
- Gates OK mantem decisao, proposta, risco aprovado e execucao bloqueados.
