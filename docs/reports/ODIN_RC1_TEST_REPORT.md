# ODIN RC1 Test Report

Date: 2026-05-09

## Testes executados
1. `pytest` (via `.venv/bin/pytest`)
2. `ruff check .` (via `.venv/bin/ruff check .`)
3. `mypy .` (via `.venv/bin/mypy .`)

## Erros encontrados
1. `pytest` inicial: falha de import dos novos módulos RC1 por `pythonpath` restrito a `src`.
2. `pytest` intermédio: falhas no `CommandBus` por serialização de dataclass `slots=True`.
3. `mypy .`: conflito de módulo duplicado `apps` (`src/apps` vs `./apps`).
4. `mypy .`: tipagem em `odin_atlas/agent_router.py` (`object` sem `analyze`).

## Erros corrigidos
1. Ajustado `pyproject.toml` para `pythonpath = ["src", "."]` no pytest.
2. Corrigido `odin_control/command_bus.py` para usar `asdict(...)`.
3. Corrigido `odin_logs/schemas.py` (`AuditEvent.to_dict`) e JSON serialization com `default=str` em logger/audit.
4. Ajustado `tool.mypy.exclude` para evitar conflito com `./apps`.
5. Tipagem explícita em `odin_atlas/agent_router.py`.

## Erros pendentes
- Nenhum erro pendente na execução final.

## Resultado final
- `pytest`: **151 passed**
- `ruff check .`: **All checks passed**
- `mypy .`: **Success: no issues found**

## Próximo passo recomendado
1. Adicionar testes de integração dedicados ao fluxo novo `apps/dashboard_html` + `apps/telegram_bot` em ambiente controlado.
