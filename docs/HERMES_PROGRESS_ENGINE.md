# Motor de Progresso e Escalamento Hermes

## Objectivo

O motor da Fase 5 decide com base em resultados verificaveis. Uma resposta do LLM local nunca e considerada prova de conclusao.

## Estados

`PENDING`, `PLANNING`, `LOCAL_EXECUTION`, `TESTING`, `LOCAL_RETRY`, `CODEX_REVIEW`, `BLOCKED`, `AWAITING_APPROVAL`, `COMPLETED` e `FAILED_SAFE`.

O estado e guardado atomicamente em `~/hermes_state/tasks`. Pacotes de revisao ficam em `~/hermes_state/escalations`. O motor apenas guarda e avalia estado; nao executa comandos, nao altera Git e nao comunica autonomamente com servicos externos.

## Progresso objectivo

Sao consideradas melhorias:

- menos testes falhados;
- mais testes aprovados;
- menos erros de lint ou tipagem;
- aumento de cobertura sem crescimento excessivo do diff.

O escalamento para Codex e imediato quando existe alteracao critica, ficheiros fora do ambito, regressao ou repeticao da mesma assinatura de erro. Sem melhoria, existe no maximo uma nova tentativa local; a segunda ausencia de progresso escala para Codex. Uma tarefa simples nunca ultrapassa tres tentativas locais.

## Pacote Codex

O pacote contem apenas objectivo, criterios de aceitacao, caminhos autorizados, tentativas, assinatura do erro, ficheiros alterados, testes falhados, metricas, diff relevante limitado e uma pergunta tecnica concreta. Nao inclui automaticamente o repositorio completo, prompts, respostas ou segredos.

## Limites

- O motor nao chama ainda o Codex automaticamente.
- O motor nao aplica codigo produzido pelo LLM.
- O motor nao faz commit, push, merge ou checkout.
- O motor nao pode alterar trading, risco, tesouraria, credenciais ou firewall.
- `COMPLETED` so pode ser atribuido por um fluxo posterior apos validacoes e revisao.
