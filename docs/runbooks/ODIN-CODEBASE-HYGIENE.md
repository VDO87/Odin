# ODIN Codebase Hygiene

## Objetivo
Manter o repositório limpo de artefactos locais e validar rapidamente a saúde técnica antes de avançar com novos cortes.

## 1) Limpeza de ficheiros lixo locais
Executar na raiz do projeto:

```bash
find . -type d -name '__pycache__' -prune -exec rm -rf {} +
find . -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '.DS_Store' -o -name '*.tmp' -o -name '*.bak' -o -name '*~' \) -delete
rm -rf .pytest_cache .mypy_cache .ruff_cache
```

Resultado esperado:
- sem `__pycache__` nem `*.pyc` em `src/` e `tests/`;
- caches de ferramentas removidas.

## 2) Validação técnica completa
```bash
./.venv/bin/pytest -q
./.venv/bin/ruff check src tests
./.venv/bin/mypy src tests
```

Resultado esperado:
- `pytest`: todos os testes passam;
- `ruff`: sem violações;
- `mypy`: sem erros de tipos.

## 3) Troubleshooting rápido
1. `pytest` falha:
- verificar regressões funcionais no ficheiro de teste indicado.

2. `ruff` falha:
- corrigir estilo/imports e voltar a correr `ruff check`.

3. `mypy` falha:
- corrigir tipos nos módulos indicados, sem alterar comportamento funcional.

## 4) Ficheiros de suporte operacional
- runbook de testes da consola: [`docs/runbooks/ODIN-TRADER-CONSOLE-TESTING.md`](/home/vdo/Secretária/Projects_Codex/Odin_Teste/docs/runbooks/ODIN-TRADER-CONSOLE-TESTING.md)
- runbook principal: [`docs/runbooks/ODIN-RUNBOOK-v0.1.md`](/home/vdo/Secretária/Projects_Codex/Odin_Teste/docs/runbooks/ODIN-RUNBOOK-v0.1.md)
- handoff de sessão: [`docs/runbooks/ODIN-SESSION-HANDOFF.md`](/home/vdo/Secretária/Projects_Codex/Odin_Teste/docs/runbooks/ODIN-SESSION-HANDOFF.md)

## 5) Sandbox isolado e fonte de verdade
- `$HOME/odin-runtime` é ambiente descartável de teste.
- a fonte de verdade é o código no repositório principal.
- não manter correções apenas no sandbox: corrigir no repositório e reinstalar sandbox.

### Reset seguro do sandbox
```bash
ODIN_HOME="$HOME/odin-runtime" scripts/odin_purge.sh --dry-run --remove-install
ODIN_HOME="$HOME/odin-runtime" scripts/odin_purge.sh --remove-install
```

### Reinstalação limpa
```bash
./INSTALL_ODIN.sh --install-root "$HOME/odin-runtime" --profile lite --skip-apt
```
