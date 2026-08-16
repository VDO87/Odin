# Aprovação de processo persistente supervisionado

## Estado por defeito

**NÃO AUTORIZADO.** ODIN não cria serviço, tarefa agendada, daemon nem processo
persistente automaticamente. TradeDesk, cockpit e refresh são sessões locais
limitadas por watchdog e podem ser terminados manualmente pelo operador.

Este documento define a aprovação humana que seria necessária antes de sequer
preparar uma operação persistente de observação. Não autoriza trading, ordens,
depósitos, login adicional, proposta financeira ou execução.

## Pré-condições obrigatórias

Registar todas como verificadas no mesmo dia da aprovação:

1. `safe_to_trade=false`, `real_trading=false` e `execution_allowed=false`.
2. Suite, smoke, Ruff, mypy direcionado e `git diff --check` verdes no commit
   identificado no registo de aprovação.
3. TradeDesk, `/cockpit`, lançador localhost e atalhos aprovados no walkthrough.
4. MT5 DEMO somente read-only, com estado reconciliado; conta real/missing/unknown
   deve bloquear.
5. Dados MT5 e públicos com frescura/qualidade válidas; dados antigos ou
   incompletos devem bloquear, nunca ser preenchidos.
6. Logs, SQLite, relatórios e redaction verificados; sem segredos no pedido,
   argumentos ou evidência.
7. CPU/GPU têm telemetria disponível ou o processo permanece bloqueado; qualquer
   valor igual ou superior a 80 °C bloqueia a carga.
8. Kill switch testado e estado de execução bloqueado confirmado após restart.

## Registo de aprovação humana

O operador deve criar um registo local sanitizado com:

```text
Data/hora UTC:
Operador:
Commit Git:
Objetivo estrito: observação local supervisionada
Duração máxima autorizada:
Frequência máxima de refresh:
Fontes permitidas:
Watchdog global:
Kill switch verificado por:
Critérios de paragem:
```

Não inserir palavras-passe, tokens, login, servidor ou dados de conta nesse
registo. A ausência de qualquer campo significa **não aprovado**.

## Requisitos mínimos se uma aprovação futura existir

- processo limitado a loopback/local;
- timeout por fornecedor, timeout global e watchdog externo Linux;
- uma única carga Ollama, sem display M4000;
- logs JSONL/SQLite sanitizados no D: e relatório por sessão;
- kill switch e paragem manual inequívoca;
- parar perante CPU/GPU >=80 °C, CUDA/OOM, fonte degradada, dados antigos,
  reconciliação inválida ou qualquer flag de execução diferente de `false`;
- não reiniciar automaticamente após uma falha; requer nova revisão humana.

## Paragem e recuperação

1. Acionar o kill switch/fechar a sessão local.
2. Não contactar o broker, não repetir pedidos e não eliminar evidência.
3. Guardar relatório sanitizado com hora, razão e processo afetado.
4. Confirmar as três flags de bloqueio através do smoke local.
5. Investigar em ramo local, validar e pedir nova aprovação antes de reiniciar.

## Limite final

Este runbook não converte ODIN num sistema autónomo e não altera permissões de
execução. Qualquer mudança para propostas DEMO ou ordens exige uma autorização
separada, específica e posterior.
