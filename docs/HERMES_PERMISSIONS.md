# Hermes Permissions

Hermes arranca em modo read-only.

Pode:

- Ler dados aprovados.
- Resumir logs.
- Criar relatorios.
- Produzir recomendacoes explicaveis.
- Apoiar o operador com notas de auditoria.
- Ler e resumir a saída sanitizada da ferramenta MT5 read-only descrita em
  `docs/runbooks/MT5_READONLY_ODIN_HERMES.md`.

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

## Fase 4 - Trabalhador Local Ollama

O adaptador Ollama e um trabalhador local delimitado. Pode produzir texto, propostas de codigo, resumos e analises, mas nao pode executar a resposta nem alterar o repositorio.

Controlos obrigatorios:

- API limitada a `127.0.0.1` ou `localhost`.
- Um unico modelo local carregado.
- Contexto, temperatura, tentativas, timeout e duracao maxima configuraveis.
- Cancelamento antes de novas tentativas e protecao contra ciclos sem progresso.
- Resultado estruturado com identificador de tarefa, estado, tentativa, duracao e metricas.
- Logs apenas com metadados; prompts, respostas e segredos ficam excluidos.
- Falhas e timeouts nao autorizam execucao, commits, merges ou trading.

O Codex continua responsavel pela supervisao tecnica e validacao. A integracao do motor persistente e do escalamento automatico pertence a fase seguinte.
