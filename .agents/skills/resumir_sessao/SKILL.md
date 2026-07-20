---
name: resumir_sessao
description: Skill operacional Hermes para resumir sessao.
version: 1.0.0
---

# resumir_sessao

## Finalidade

Executar resumir sessao em modo seguro, mantendo `REAL_TRADING=false` e `SAFE_TO_TRADE=false`.

## Parametros

- `contexto`
- `timeout`

## Permissoes

- `read_only` quando aplicavel
- `safe_actions_only`

## Pre-condicoes

- runtime seguro validado
- risco e execucao bloqueados

## Passos

1. Ler o contexto minimo necessario.
2. Executar apenas passos autorizados.
3. Validar o resultado.
4. Registar memoria e checkpoint quando relevante.

## Validacoes

- resultado estruturado
- sem desbloquear trading real
- sem remocao de protecoes

## Resultado Esperado

Relatorio seguro, auditavel e reutilizavel pelo supervisor.

## Erros Possiveis

- dependencia_ausente
- timeout
- estado_invalido

## Recuperacao

Manter fail-closed, registar incidente e escalar apenas com contexto minimo.

## Testes

- estrutura_skill
- validacao_registry

## Versao

`1.0.0`
