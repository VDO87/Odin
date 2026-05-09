# ODIN-POST-F7-BACKLOG
## Projeto Odin

**Data de referência:** 2026-04-28  
**Estado:** Ativo  
**Objetivo:** Definir o backlog técnico após o fecho do corte principal F7, sem criar uma F8 formal no roadmap.

> Nota operacional: para retoma diária, comandos de teste e estado consolidado de runtime,
> usar `docs/runbooks/ODIN-SESSION-HANDOFF.md`.

---

## 1. Enquadramento

O roadmap atual termina em F7 como fase formal.  
Depois do fecho de F7, o trabalho continua como backlog priorizado e governado por evidência, não por nova fase implícita.

Este backlog é a decisão oficial pós-F7 e substitui decisões ad-hoc de curto prazo.

---

## 2. Princípios de priorização

1. segurança operacional antes de novos surfaces;
2. fechar requisitos `P1` ainda em `PLANNED` na rastreabilidade;
3. privilegiar evidência testável (`unit`, `integration`, `fault_injection`, `scenario`);
4. só abrir capacidades novas quando não degradarem `CORE`, `RISK`, `EXEC` e `RECOVERY`.

---

## 3. Backlog priorizado

| backlog_id | prioridade | objetivo | requisitos alvo | entregáveis mínimos | critério de fecho |
|---|---|---|---|---|---|
| BF7-01 | P0 | Endurecer contratos de estado e bloqueios no CORE/RECOVERY | `REQ-CORE-002`, `REQ-CORE-005`, `REQ-CORE-006`, `REQ-RECOVERY-003` | guards formais de transição, vetor completo de bloqueios visível no estado interno, testes de precedência kill/manual/recovery | testes unit/integration verdes + requisitos marcados `TESTED` na matriz |
| BF7-02 | P0 | Fechar núcleo de segurança operacional de RISK + EXEC | `REQ-RISK-001..004`, `REQ-EXEC-001..005` | cenários de bloqueio por risco, expiração de intenção, slippage, divergência e idempotência com evidência persistida | suites críticas verdes + reason codes estáveis em falhas críticas |
| BF7-03 | P1 | Completar observabilidade operacional no DASH | `REQ-DASH-003` | projeção explícita do vetor completo de bloqueios ativos, sem perda de causa raiz | integração `CORE -> DASH` validada + documentação `SDS-600` alinhada |
| BF7-04 | P1 | Abrir queries históricas de LEARN no DASH | extensão de `REQ-LEARN-001..003` / `SDS-800` | queries por `proposal_id` e janela temporal via `DASH` com resposta auditável | integração LEARN+DASH verde + contratos documentados |
| BF7-05 | P1 | Fechar evidência de maturidade operacional pós-F7 | critérios transversais do test plan | drills de runbook (recovery, kill, bloqueio manual), evidência de fault-injection, atualização de rastreabilidade e changelog por corte | pacote documental e de testes pronto para operação continuada |

---

## 4. Sequência de execução decidida

Ordem obrigatória:

1. `BF7-01`
2. `BF7-02`
3. `BF7-03`
4. `BF7-04`
5. `BF7-05`

Racional:
- `BF7-01` e `BF7-02` fecham risco de comportamento incorreto no núcleo;
- `BF7-03` e `BF7-04` expandem surface de supervisão sem inverter prioridade;
- `BF7-05` consolida evidência e governança do ciclo.

---

## 5. Regra de governação deste backlog

- não criar “F8” implícita sem revisão explícita de `ODIN-IMPLEMENTATION-ROADMAP.md`;
- cada item fechado deve atualizar:
  - `ODIN-TRACEABILITY-MATRIX.md`
  - `ODIN-TEST-PLAN.md` (se houver novo tipo de evidência)
  - `CHANGELOG.md`
- nenhum item `P0` pode ser contornado por item `P1`.

---

## 6. Próxima execução recomendada

Iniciar implementação por `BF7-01`, com corte técnico dedicado a:
- guards de transição em `CORE`;
- precedência formal de bloqueios (`kill`, manual, recovery pendente);
- testes de integração e fault-injection para cenários de precedência.

---

## 7. Estado de execução

### 7.1 Atualização 2026-04-28

- `BF7-01`: **CONCLUÍDO**
  - guards de transição endurecidos com precedência explícita;
  - vetor completo de bloqueios exposto no estado interno (`health_metrics.active_block_vector`);
  - cobertura adicionada para precedência `kill/manual/recovery` em unit + integration;
  - requisitos `REQ-CORE-002`, `REQ-CORE-005`, `REQ-CORE-006` e `REQ-RECOVERY-003` atualizados para `TESTED` na matriz.
- `BF7-02`: **CONCLUÍDO**
  - `RISK` propaga `reason_code` estável para o `CORE` em bloqueio e kill;
  - `EXEC` estabiliza reason codes em falhas críticas (`intent_expired`, slippage/divergence);
  - ledger de execução comprova expiração, slippage/divergência e deduplicação (`was_deduplicated`);
  - requisitos `REQ-RISK-001..004` e `REQ-EXEC-001..005` atualizados para `TESTED`.
