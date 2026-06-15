# Architecture Lock

ODIN_HERMES_ALIVE arranca na fase A0 - Bootstrap. A arquitectura fica separada por responsabilidades:

- Core: orquestracao operacional e estado.
- Risk: limites, bloqueios e validacao de seguranca financeira.
- Treasury: capital, liquidez, fiscalidade operacional e regras de dinheiro.
- Hermes: camada cognitiva read-only para memoria, RAG, relatorios e recomendacoes.
- Dashboard: cockpit humano para auditoria, logs e decisao assistida.
- Adapters: integracoes externas isoladas.

Bloqueios estruturais:

- Trading real esta bloqueado por defeito.
- `mt5.order_send` e proibido.
- XTB nao pode ser automatizado para clicar ou enviar ordens.
- Hermes nao aprova nem executa operacoes.
- Risk vence sempre Hermes.
- Treasury vence sempre Hermes em materia de dinheiro.

## A1 - Core Vivo + Logging Base

O runtime minimo arranca em `OFF_SAFE`, com `safe_to_trade=false`, `real_trading=false`, Risk em `READY_BLOCKING` e Hermes em `READ_ONLY`.

O comando `python -m odin.cli validate` apenas valida e regista estado seguro em JSONL e SQLite. Nao existe integracao operacional de broker nesta fase.

## A6 - Market Watch

`MARKET_WATCH` e um modo de observacao com dados mock. Pode alterar o campo `mode` da resposta, mas nao pode desbloquear trading, gerar decisoes operacionais ou criar execucao.

## A7 - Data Quality Gates

Gates de qualidade sao bloqueantes e informativos. Um resultado `OK` nao autoriza decisoes, trading real ou execucao.

## A8 - Strategy Baseline

Estrategias existem apenas como observacao tecnica. A baseline pode ler qualidade de dados, mas nao pode gerar sinais, propostas, tamanho de posicao ou execucao.

## A9 - Decision Intent

Decision Intent existe apenas como estrutura bloqueada. Pode ler o estado da estrategia, mas deve devolver `NO_DECISION`, nao aprovar risco, nao criar parametros de ordem e nao desbloquear execucao.

## A10 - Risk Gate

Risk Gate e bloqueante por desenho. Pode ler Decision Intent, mas deve devolver `BLOCKED`, manter `risk_approved=false` e nunca criar aprovacao operacional.

## A11 - Shadow Proposal

Shadow Proposal e apenas uma estrutura bloqueada em modo sombra. Pode ler Risk Gate, mas nao deve criar direccao de mercado, parametros de ordem, aprovacao de risco ou execucao.

## A12 - Runtime Smoke

Runtime Smoke e apenas validacao local agregada. Deve chamar modulos internos, confirmar estado seguro e bloqueante, e nunca executar comandos externos ou activar trading.

## A13 - v0.1.0-local-safe-runtime

`v0.1.0-local-safe-runtime` fecha a primeira base local segura. Esta release candidate nao contem execucao real, nao contem integracao real MT5, nao contem XTB API, nao contem sinais BUY/SELL, nao contem parametros `entry`/`stop_loss`/`take_profit` e nao contem position sizing.

Os bloqueios permanecem obrigatorios: `real_trading=false`, `safe_to_trade=false`, `execution_allowed=false`, Hermes `READ_ONLY`, Treasury `READ_ONLY`, Risk `READY_BLOCKING`, Risk Gate `BLOCKED` e Shadow Proposal `BLOCKED`.

## A14 - MT5 Bridge Mock Adapter

A14 permite apenas contrato e adaptador mock para a futura ponte MT5. O estado deve permanecer `MOCK_ONLY`, sem terminal real, sem conta ligada, sem login, sem credenciais, sem broker real e sem ordens.

Os flags criticos continuam imutaveis: `real_trading=false`, `safe_to_trade=false` e `execution_allowed=false`.

## A15 - MT5 Symbol Mapping Mock

A15 permite apenas mapeamento mock de simbolos entre Odin e uma futura bridge MT5. O mapeamento nao autoriza risco, nao cria sinais, nao cria ordens, nao calcula tamanho de posicao e nao liga a terminal real.

Forex pode ser marcado como tradable em mock; ativos FIRE devem permanecer classificados como `non_mt5_fire_asset`. Os flags criticos continuam `real_trading=false`, `safe_to_trade=false` e `execution_allowed=false`.

## A16 - MT5 Market Feed Mock

A16 permite apenas feed mock de mercado baseado no mapeamento A15. O feed pode publicar ticks determinísticos para `EURUSD`, `USDJPY` e `GBPUSD`, mas ativos FIRE nao entram no feed MT5 mock.

O feed permanece `MOCK_ONLY`, `connected=false` e nunca altera os flags criticos: `real_trading=false`, `safe_to_trade=false` e `execution_allowed=false`.

## A17 - MT5 Feed Quality Gates

A17 permite apenas gates de qualidade sobre o feed MT5 mock. Um resultado `OK` confirma consistencia dos ticks mock, mas nao autoriza decisao, risco, trading real ou execucao.

Os flags permanecem obrigatorios: `safe_to_use_for_decision=false`, `real_trading=false`, `safe_to_trade=false` e `execution_allowed=false`.

## A18 - Feed Source Selector

A18 permite apenas selecionar uma fonte observacional mock entre `market_data_mock` e `mt5_feed_mock`. A preferencia por `mt5_feed_mock` nao cria autorizacao para decisao, risco ou execucao.

Os flags permanecem obrigatorios: `safe_to_use_for_decision=false`, `real_trading=false`, `safe_to_trade=false` e `execution_allowed=false`.
