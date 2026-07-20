# Validação WSL do ODIN

Use `scripts/validate_wsl.sh` na raiz do worktree ODIN.

O script aplica `ulimit -n 8192` por defeito, executa o smoke local
fail-closed, a suite completa e Ruff. Isto evita a falha de descritores
abertos observada na distro recuperada.

## Limites por defeito

- Smoke: 240 segundos
- Suite completa: 600 segundos
- Descritores: 8192

Pode ajustar sem editar o script:

```sh
ODIN_TEST_TIMEOUT=900 ODIN_RUFF_BIN="$HOME/.local/share/pipx/venvs/ruff/bin/ruff" \
  scripts/validate_wsl.sh
```

O script não faz push, merge, chamadas externas, trading, nem inicia um daemon.
