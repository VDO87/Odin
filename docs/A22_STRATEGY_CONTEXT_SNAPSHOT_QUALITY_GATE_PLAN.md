# A22 - Strategy Context Snapshot Quality Gate

## Estado de prontidao

- Repositorio base: `/home/odin/projects/odin`.
- Branch dedicada: `a22/strategy-context-snapshot-quality`.
- Worktree dedicada: `/home/odin/worktrees/a22-strategy-context-snapshot-quality`.
- Base esperada: `32ff6f4 feat: implement A21 strategy context snapshot`.
- A21 fornece `StrategyContextSnapshot`, fingerprint SHA-256 deterministico, CLI `strategy-context-snapshot`, endpoint `/strategy/context/snapshot` e smoke com 18 modulos.
- A22 deve ser observacional e fail-closed. Um resultado `OK` significa apenas que o snapshot A21 e coerente e continua bloqueado.

## Objectivo

Criar um gate de qualidade sobre o snapshot A21 que valide presenca, schema, versao, modo, fingerprint deterministico, fontes observacionais e flags criticos bloqueados.

A22 nao interpreta mercado, nao gera decisao, nao cria proposta, nao aprova risco, nao desbloqueia execucao e nao ativa trading real.

## Contrato

Nome do contrato: `StrategyContextSnapshotQualityReport`.

Campos previstos:

- `component="strategy_context_snapshot_quality"`;
- `status`, `OK` apenas quando todos os gates obrigatorios passam;
- `quality_mode="SNAPSHOT_QUALITY_GATE"`;
- `quality_version="A22.v1"`;
- `snapshot_mode`;
- `snapshot_version`;
- `selected_source`;
- `primary_symbol`;
- `context_fingerprint`;
- `recomputed_fingerprint`;
- `fingerprint_valid`;
- `schema_valid`;
- `required_fields_present`;
- `quality_gates_passed`;
- `flags_blocked`;
- `gates_count`;
- `gates_passed`;
- `safe_to_use_for_decision=false`;
- `decision_generated=false`;
- `trade_proposal_generated=false`;
- `risk_approved=false`;
- `execution_allowed=false`;
- `safe_to_trade=false`;
- `real_trading=false`;
- `reason`;
- `gates`;
- `blockers`;
- `notes`.

O contrato usa `@dataclass(frozen=True)` e serializa listas de forma estavel.

## Invariantes

1. `snapshot_mode` tem de ser `MOCK_OBSERVATION_ONLY`.
2. `snapshot_version` tem de ser `A21.v1`.
3. Todos os campos obrigatorios A21 têm de existir.
4. `selected_source` e `primary_symbol` nao podem ser vazios.
5. O fingerprint recalculado sobre os campos A21 aprovados tem de coincidir com `context_fingerprint`.
6. `quality_gates_passed` tem de ser `true`, mas isso nunca autoriza decisao.
7. Todos os flags criticos têm de ser `false`.
8. Qualquer inconsistencia devolve `BLOCKED` com blockers explicaveis.

## Ficheiros previstos

- `src/odin/contracts/strategy_context_snapshot_quality.py`.
- `src/odin/decision/strategy_context_snapshot_quality.py`.
- `src/odin/contracts/events.py`.
- `src/odin/cli.py`.
- `src/odin/dashboard/routes.py`.
- `src/odin/dashboard/schemas.py`.
- `src/odin/core/smoke.py`.
- `tests/test_a22_strategy_context_snapshot_quality.py`.
- `tests/test_a22_strategy_context_snapshot_quality_contracts.py`.
- `tests/test_a22_strategy_context_snapshot_quality_cli_dashboard.py`.
- `tests/test_a22_strategy_context_snapshot_quality_guards.py`.
- Documentacao em `README.md`, `CHANGELOG.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE_LOCK.md` e `docs/DASHBOARD_SPEC.md`, conforme aplicavel.

## Testes

- Contrato congelado e serializacao estavel.
- Fingerprint valido passa.
- Fingerprint alterado falha.
- Versao errada falha.
- Modo errado falha.
- Campo obrigatorio ausente falha.
- Fonte ou simbolo vazio falha.
- Qualquer flag critico `true` falha.
- Entrada invalida nao desbloqueia runtime.
- CLI retorna JSON read-only.
- Endpoint retorna o mesmo contrato.
- Smoke inclui A22 e `modules_count=19`.
- Guardas rejeitam termos operacionais proibidos.
- Testes A0-A21 permanecem verdes.

## Riscos

- Confundir consistencia do snapshot com autorizacao decisoria.
- Divergir do algoritmo de fingerprint A21.
- Aumentar o smoke para 19 sem atualizar testes historicos.
- Introduzir termos operacionais proibidos em runtime ou testes.

## Rollback

1. Trabalhar apenas na branch/worktree A22.
2. Manter commits locais pequenos.
3. Nao fazer push, merge ou rebase destrutivo.
4. Se A22 falhar validacao, preservar o diff e nao integrar em `master`.
5. Reverter a worktree/branch apenas com aprovacao humana explicita.

## Impacto no smoke

O smoke passa de 18 para 19 modulos seguros com `strategy-context-snapshot-quality`. O novo modulo deve confirmar consistencia observacional e manter `safe_to_trade=false`, `real_trading=false`, `execution_allowed=false` e `trade_proposal_generated=false`.
