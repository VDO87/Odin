# ODIN F7 Handoff

**Data de referência:** 2026-04-28  
**Fase ativa:** F7 — Evolução controlada  
**Estado do roadmap:** continua a ser F7; não existe F8 formal no roadmap ou no test plan atuais.

> Nota de retoma: este documento mantém o fecho histórico do corte F7.
> Para estado operacional corrente, validação técnica e comandos de retoma usar:
> `docs/runbooks/ODIN-SESSION-HANDOFF.md`.

Este ficheiro é o ponto de retoma do corte F7.  
Se a sessão ou a máquina cair, retomar a partir daqui.

## 1. Estado atual

### 1.1 Itens fechados

**Item 1 — Ações LEARN reais no dispatch do DASH**  
Concluído no código.

Implementado:
- `LEARN_ACTION_REVIEW_APPROVAL`
- `LEARN_ACTION_EVALUATE_PROMOTION`
- `LEARN_ACTION_START_SHADOW`
- `LEARN_ACTION_COMPLETE_SHADOW`
- `LEARN_ACTION_ACTIVATE_PROPOSAL`
- `LEARN_ACTION_TRIGGER_ROLLBACK`

Ficheiros principais:
- `src/dash/domain.py`
- `src/core/runtime.py`
- `tests/integration/test_learn_dash_core_flow.py`

**Item 2 — Consultas LEARN explícitas no DASH**  
Concluído no código.

Implementado:
- payload explícito `learn_query_results` no resultado do DASH
- queries explícitas:
  - `LEARN_QUERY_PROPOSAL`
  - `LEARN_QUERY_APPROVAL`
  - `LEARN_QUERY_SHADOW_AUDIT`
  - `LEARN_QUERY_SHADOW_RECOMMENDATION`
  - `LEARN_QUERY_ACTIVE_VERSION`
  - `LEARN_QUERY_ROLLBACK_AUDIT`
- `learn_shadow_audit`
- `learn_operational_hints`
- ligação do DASH ao `LearningOrchestrator` sem acoplamento direto ao store

Ficheiros principais:
- `src/dash/domain.py`
- `src/learn/domain.py`
- `tests/integration/test_learn_dash_core_flow.py`

**Item 3 — Persistência auditável completa**  
Concluído no código.

Implementado:
- leituras auditáveis por `proposal_id` e por janela temporal
- histórico próprio para approvals sem quebrar a visão `latest`
- listas auditáveis de:
  - proposals
  - approvals
  - shadow sessions
  - promotion decisions
  - rollback records

Ficheiros principais:
- `src/persistence/state_store.py`
- `src/persistence/sqlite_state_store.py`
- `src/learn/domain.py`
- `tests/unit/test_learn_module.py`
- `tests/integration/test_learn_dash_core_flow.py`

**Item 4 — Cenários negativos e de governação**  
Concluído no código.

Implementado:
- ativação bloqueada com:
  - `approval_pending`
  - `approval_rejected_or_blocked`
  - `shadow_session_required`
  - `shadow_rejected_candidate`
  - `shadow_requires_rollback`
  - `core_activation_not_allowed`
  - `risk_context_incompatible`
- rollback bloqueado com:
  - `missing_active_version`
  - `missing_recoverable_snapshot`
- erro explícito ao completar shadow sem sessão
- mapeamento de erros de domínio do LEARN para rejeições explícitas no DASH
- validação de ações inválidas ou indisponíveis no dispatch do DASH

Ficheiros principais:
- `src/learn/domain.py`
- `src/dash/domain.py`
- `tests/unit/test_learn_module.py`
- `tests/integration/test_learn_dash_core_flow.py`

**Item 5 — Validação completa**  
Concluído no ambiente atual.

Passou:
- `./.venv/bin/python -m pytest -q` -> `76 passed`
- `./.venv/bin/python -m ruff check src tests` -> `All checks passed`
- `./.venv/bin/python -m mypy src tests` -> `Success: no issues found`

**Item 6 — Atualização formal da documentação**  
Concluído neste corte.

Atualizado:
- `README.md`
- `docs/sds/SDS-600-DASH.md`
- `docs/sds/SDS-800-LEARN.md`
- `docs/plans/ODIN-TEST-PLAN.md`
- este próprio handoff

### 1.2 Estado resumido

Neste momento:
- o corte principal de F7 está implementado no código;
- o corte principal de F7 está validado localmente;
- o gate de tipagem estática (`mypy`) está verde no baseline atual;
- o contrato público do DASH para LEARN já está documentado;
- a trilha auditável do LEARN já não depende apenas de leituras `latest`;
- não há bloqueador aberto nos itens 1 a 6.

## 2. Surface público relevante

### 2.1 Ações LEARN no DASH
- `LEARN_ACTION_REVIEW_APPROVAL`
- `LEARN_ACTION_EVALUATE_PROMOTION`
- `LEARN_ACTION_START_SHADOW`
- `LEARN_ACTION_COMPLETE_SHADOW`
- `LEARN_ACTION_ACTIVATE_PROPOSAL`
- `LEARN_ACTION_TRIGGER_ROLLBACK`

### 2.2 Queries LEARN explícitas
- `LEARN_QUERY_PROPOSAL`
- `LEARN_QUERY_APPROVAL`
- `LEARN_QUERY_SHADOW_AUDIT`
- `LEARN_QUERY_SHADOW_RECOMMENDATION`
- `LEARN_QUERY_ACTIVE_VERSION`
- `LEARN_QUERY_ROLLBACK_AUDIT`

### 2.3 Campos públicos já expostos no DASH
- `last_change_summary`
- `learn_shadow_audit`
- `learn_operational_hints`
- `learn_query_results`
- `blocking_reason_code`
- `blocking_summary`

## 3. Validação de retoma

Se for preciso confirmar rapidamente o estado após retoma:

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m ruff check src tests
./.venv/bin/python -m mypy src tests
```

## 4. Próxima ação recomendada

O F7 deixou de ter um corte técnico urgente em aberto.  
O próximo trabalho recomendado é um destes:

1. atualizar `ODIN-TRACEABILITY-MATRIX.md` e `CHANGELOG.md` para refletir o fecho do corte F7;  
2. decidir o backlog pós-F7, já que não existe F8 formal no roadmap atual;  
3. se houver necessidade operacional real, abrir um corte novo para queries históricas do LEARN diretamente no DASH.

### 4.1 Estado após retoma (2026-04-28)

- item 1 concluído;
- item 2 concluído com backlog formal em `docs/plans/ODIN-POST-F7-BACKLOG.md`;
- item 3 executado no corte pós-F7 (`BF7-04` inicial): `DASH` com query histórica explícita (`LEARN_QUERY_HISTORY`) por `proposal_id` e janela temporal.

### 4.2 Decisão de fecho (2026-04-28)

- o F7 fica formalmente em estado **encerrado/estável**;
- trabalho subsequente deve seguir backlog `BF7-01..BF7-05` sem criação de nova fase formal.

## 5. Nota operacional

Se a máquina desligar inesperadamente, retomar por esta ordem:

1. abrir este ficheiro;  
2. correr os três comandos de validação da secção 3;  
3. confirmar no `README.md` que o estado documental bate certo com este handoff;  
4. escolher uma das ações da secção 4.
