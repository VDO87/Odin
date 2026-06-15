# Hermes Permissions

Hermes arranca em modo read-only.

Pode:

- Ler dados aprovados.
- Resumir logs.
- Criar relatorios.
- Produzir recomendacoes explicaveis.
- Apoiar o operador com notas de auditoria.

Nao pode:

- Enviar ordens.
- Aprovar trading real.
- Alterar limites de risco.
- Alterar regras de tesouraria.
- Criar ou ler secrets reais.
- Contornar bloqueios do Core, Risk ou Treasury.

## A3 - Resumo Read-Only

Hermes pode gerar resumos e recomendacoes a partir de estado seguro e logs JSONL.

Todos os outputs devem declarar `read_only=true`. Recomendacoes devem exigir revisao humana e declarar `can_execute=false`.
