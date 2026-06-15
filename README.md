# ODIN_HERMES_ALIVE

Fundacao limpa para a fase A0 - Bootstrap.

ODIN e o motor operacional: core, risco, dados, logs, tesouraria e execucao controlada. Hermes e a camada cognitiva: memoria, RAG, relatorios, recomendacoes e apoio ao operador. O Dashboard e o cockpit humano para auditoria, logs e decisao assistida.

Estado inicial:

- Trading real bloqueado por defeito.
- Hermes em modo read-only.
- MT5 limitado a Market Watch, Shadow Decision e Demo futura.
- XTB limitado a operacao manual/assistida, sem cliques automaticos.
- Codex limitado a engenharia interna em staging/desenvolvimento.

Este projecto ainda nao implementa logica funcional de trading.

## Validacao rapida

```bash
find ODIN_HERMES_ALIVE -maxdepth 4 -type f | sort
python3 -m tomllib ODIN_HERMES_ALIVE/pyproject.toml
```
