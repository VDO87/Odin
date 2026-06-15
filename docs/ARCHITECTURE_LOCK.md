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
