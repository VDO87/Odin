# ODIN Remote Branch Audit

## Escopo
- Inventário de `refs/remotes/origin/*` com análise de contenção e unicidade relativa a `origin/release/rc1` e `origin/archive/legacy-main-before-rc1`.
- Nesta fase não foi apagada nenhuma branch `codex/*`.

## Tabela de auditoria

| Branch | Último commit | Data (ISO 8601) | Contida em release/rc1 | Contida em archive/legacy-main-before-rc1 | Commits únicos vs release/rc1 | Recomendação |
|---|---|---|---|---|---:|---|
| `origin/archive/legacy-main-before-rc1` | `f35941a` Merge pull request #18 from VDO87/codex/adicionar-logger-e-troca-de-tema | `2025-06-25T00:14:08+01:00` | no | yes | 35 | `KEEP` |
| `origin/codex/adicionar-logger-e-troca-de-tema` | `f2cb5c4` Add logger and theme toggle to dashboard | `2025-06-25T00:13:18+01:00` | no | yes | 34 | `ARCHIVE` |
| `origin/codex/adicionar-testes-unitários-para-gerar_feedback` | `93d62c1` Expand feedback tests | `2025-06-24T22:34:14+01:00` | no | yes | 14 | `ARCHIVE` |
| `origin/codex/adicionar-workflow-github-actions` | `2d38d20` Add lint steps to CI | `2025-06-24T18:31:36+01:00` | no | yes | 6 | `ARCHIVE` |
| `origin/codex/ajustar-documentação-e-onboarding` | `d02bb1d` Add simulation scenarios and update docs | `2025-06-24T18:40:13+01:00` | no | yes | 8 | `ARCHIVE` |
| `origin/codex/criar-dashboard-interativo-com-dash` | `ec25c9a` Add interactive dashboard with Dash | `2025-06-24T23:45:42+01:00` | no | yes | 32 | `ARCHIVE` |
| `origin/codex/criar-esqueleto-para-módulo-ai/openai` | `0b2c931` Add OpenAI and XTB client stubs | `2025-06-24T23:31:04+01:00` | no | yes | 28 | `ARCHIVE` |
| `origin/codex/criar-estrutura-do-repositório-odin-v3.0.0` | `c703152` Merge pull request #2 from VDO87/main | `2025-06-24T18:26:50+01:00` | no | no | 4 | `KEEP` |
| `origin/codex/criar-readme.md-informativo-para-odin-zero-v3.0.0` | `d12d7df` docs: add simplified README | `2025-06-24T22:54:22+01:00` | no | yes | 20 | `ARCHIVE` |
| `origin/codex/criar-testes-automatizados-para-módulos-não-cobertos` | `7bc4f91` test: add coverage for engine and strategies | `2025-06-24T23:19:04+01:00` | no | yes | 24 | `ARCHIVE` |
| `origin/codex/criar-testes-automatizados-para-plot_pesos.py` | `5895f46` Add plot_pesos tests and improve validation | `2025-06-24T22:44:33+01:00` | no | yes | 16 | `ARCHIVE` |
| `origin/codex/criar-testes-para-cada-módulo` | `993cd6e` Add module-specific tests | `2025-06-24T18:28:26+01:00` | no | yes | 4 | `ARCHIVE` |
| `origin/codex/criar-testes-unitários-para-adaptiveai` | `534672c` Add tests for AdaptiveAI weight updates and file saving | `2025-06-24T22:49:02+01:00` | no | yes | 18 | `ARCHIVE` |
| `origin/codex/criar-testes-unitários-para-clientes-de-api` | `475dd40` Add stub modules and openai client tests | `2025-06-24T23:38:33+01:00` | no | yes | 30 | `ARCHIVE` |
| `origin/codex/criar-workflow-ci/cd-com-pytest-e-flake8` | `d8fc494` Add Python tests CI workflow | `2025-06-24T23:25:27+01:00` | no | yes | 26 | `ARCHIVE` |
| `origin/codex/revisar-e-ajustar-readme` | `f5ec189` Add MIT license and update README | `2025-06-24T23:02:43+01:00` | no | yes | 22 | `ARCHIVE` |
| `origin/codex/revisar-e-melhorar-ficheiro-readme.md` | `6684fe3` Merge pull request #5 from VDO87/codex/ajustar-documentação-e-onboarding | `2025-06-24T18:40:54+01:00` | no | yes | 9 | `ARCHIVE` |
| `origin/codex/verificação-de-qualidade-de-código-e-melhorias` | `b303a94` Add simulation cycle, docs and tests | `2025-06-24T22:20:59+01:00` | no | yes | 12 | `ARCHIVE` |
| `origin/kttiz1-codex/revisar-e-melhorar-ficheiro-readme.md` | `9c9015f` Atualiza README com exemplos e badges | `2025-06-24T21:56:49+01:00` | no | yes | 10 | `ARCHIVE` |
| `origin/main` | `f35941a` Merge pull request #18 from VDO87/codex/adicionar-logger-e-troca-de-tema | `2025-06-25T00:14:08+01:00` | no | yes | 35 | `KEEP` |
| `origin/release/rc1` | `493494c` ODIN RC1.2: document successful GitHub publish and pending cleanup | `2026-05-09T16:16:35+01:00` | yes | no | 0 | `KEEP` |

## Critério de recomendação
- `KEEP`: branch principal/arquivo ou com valor atual para referência ativa.
- `ARCHIVE`: branch com valor histórico fora de release, preferencialmente manter até consolidação.
- `DELETE_CANDIDATE`: branch já totalmente contida em `release/rc1` (sem commits únicos).

## Comandos sugeridos (não executados)
```bash
# Revisar candidatas a remoção
git branch -r | rg 'origin/(codex|kttiz1-codex)'

# Exemplo de remoção após aprovação explícita
# git push origin --delete <branch>
```
