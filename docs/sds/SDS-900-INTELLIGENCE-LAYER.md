# SDS-900 — INTELLIGENCE LAYER
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Software Design Specification  
**Domínio:** Camada advisory para cenários, reasoning e memória auxiliar, sem autoridade operacional.

---

## 1. Finalidade do documento

Este documento define a especificação técnica inicial da **ODIN INTELLIGENCE LAYER**.

Objetivo desta camada:
- produzir cenários e stress-tests operacionais (estilo Aladdin-like);
- produzir aconselhamento de reasoning tático/operacional (estilo Mythos-like);
- consultar memória auxiliar para contexto histórico (estilo MemPalace-like).

Regra central:
- esta camada é **advisory**, nunca autoritativa.

---

## 2. Âmbito técnico

### 2.1 Incluído
- boundaries funcionais e de segurança;
- contratos técnicos de advisory;
- gating por profile (`lite`, `standard`, `full`);
- proposta de estrutura de código em `src/intelligence/`;
- plano de testes inicial (sem implementação pesada).

### 2.2 Excluído neste corte
- integração OpenAI em produção;
- integração Telegram;
- integração XTB/MT5;
- execução automática de ordens;
- mutação direta de estado crítico.

---

## 3. Princípios obrigatórios

1. **Não-autoritativo por definição**  
   A camada só observa, analisa e aconselha.

2. **Sem mutação direta de módulos críticos**  
   Não pode alterar diretamente `CORE`, `RISK`, `EXEC`, `RECOVERY`.

3. **Sem desbloqueio operacional**  
   Não pode limpar bloqueios, kill, fault ou recovery pending.

4. **Sem execução**  
   Não pode executar ordens nem acionar transporte de execução.

5. **Auditabilidade de influência**  
   Qualquer influência em `DECISION`/`LEARN` deve ficar congelada em `advisory_snapshot`.

---

## 4. Posicionamento arquitetural

### 4.1 Leitura macro

```text
                +-----------------------------+
                |     INTELLIGENCE LAYER      |
                | scenario + reasoning + mem  |
                +--------------+--------------+
                               |
                 advisory only | (requests/responses/snapshots)
                               v
MARKET -> DECISION -> EXEC ----+----> RECOVERY
    \        ^         |                ^
     \       |         v                |
      -> RISK --------> CORE ---------- +
                         |
                         v
                        DASH
                         ^
                         |
                        LEARN
```

### 4.2 Responsabilidade
- produzir `advisory_response` para consumidores autorizados;
- nunca publicar eventos que alterem estado global do CORE;
- nunca invocar fluxo de execução operacional.

---

## 5. Gating por profile

| Profile | Estado da camada | Comportamento |
|---|---|---|
| `lite` | desligada por defeito | diagnóstico manual opcional, sem pipeline contínuo |
| `standard` | advisory parcial | cenários leves e regras determinísticas, sem LLM contínuo |
| `full` | advisory completo | memória auxiliar + advisory OpenAI + suporte a LEARN |

Regras:
- transição de capacidade deve respeitar profile ativo do runtime;
- profile não autorizado deve devolver `advisory_response.status = rejected` com reason explícito.

---

## 6. Boundaries e controlos de segurança

### 6.1 Operações proibidas
- alterar `GlobalStateSnapshot`;
- escrever `BlockEntry`/`ActiveBlockVector`;
- escrever `PersistentKillState`;
- invocar engines de execução (`DemoExecutionEngine`, `ControlledRealExecutionEngine`);
- limpar bloqueios manuais/kill/recovery.

### 6.2 Operações permitidas
- leitura de estado público do CORE;
- leitura de histórico auditável (quando permitido);
- análise de cenários e geração de aconselhamento;
- geração de snapshot advisory para congelamento de contexto.

### 6.3 Guardrail de integração
Toda chamada externa da camada deve passar por um `IntelligenceGuard` que valide:
- profile;
- permissões;
- escopo de uso (`decision`, `learn`, `dash_query`, `manual_diagnostic`);
- nível de sensibilidade da operação.

---

## 7. Contratos técnicos

## 7.1 `advisory_request`

Campos mínimos:

| Campo | Obrigatório | Descrição |
|---|---|---|
| `request_id` | Sim | ID único |
| `requested_at_utc` | Sim | timestamp UTC |
| `requested_by` | Sim | origem técnica/humana |
| `request_scope` | Sim | `decision`, `learn`, `dash_query`, `manual_diagnostic` |
| `execution_profile` | Sim | `lite`, `standard`, `full` |
| `target_module` | Sim | `DECISION` ou `LEARN` |
| `scenario_context` | Recomendado | contexto de cenário |
| `memory_context_ref` | Opcional | referência de memória auxiliar |
| `constraints` | Opcional | limites adicionais de advisory |

## 7.2 `advisory_response`

Campos mínimos:

| Campo | Obrigatório | Descrição |
|---|---|---|
| `response_id` | Sim | ID único |
| `request_id` | Sim | referência ao pedido |
| `status` | Sim | `accepted`, `restricted`, `rejected`, `error` |
| `reason_code` | Sim | motivo principal |
| `summary` | Sim | resumo curto advisory |
| `recommendations` | Não | lista de recomendações |
| `risk_flags` | Não | flags de risco derivadas |
| `confidence_score` | Não | confiança normalizada `[0..1]` |
| `emitted_at_utc` | Sim | timestamp UTC |
| `advisory_snapshot_id` | Não | snapshot congelado associado |

## 7.3 `advisory_snapshot`

Objetivo:
- congelar o contexto advisory efetivamente usado em ciclos `DECISION`/`LEARN`.

Campos mínimos:

| Campo | Obrigatório | Descrição |
|---|---|---|
| `advisory_snapshot_id` | Sim | ID único |
| `request_id` | Sim | pedido que originou o snapshot |
| `created_at_utc` | Sim | timestamp UTC |
| `execution_profile` | Sim | profile ativo no momento |
| `target_module` | Sim | `DECISION` ou `LEARN` |
| `scenario_context` | Sim | cenário efetivo congelado |
| `memory_context_ref` | Não | referência de memória usada |
| `response_digest` | Sim | hash/digest da resposta advisory |
| `guardrail_evaluation` | Sim | resultado de guards aplicados |

## 7.4 `scenario_context`

Campos mínimos:

| Campo | Obrigatório | Descrição |
|---|---|---|
| `scenario_id` | Sim | ID do cenário |
| `market_regime` | Sim | regime/estado de mercado |
| `risk_envelope` | Sim | envelope de risco aplicado |
| `stress_hypotheses` | Não | hipóteses de stress |
| `time_horizon` | Não | horizonte de análise |
| `assumptions` | Não | pressupostos explícitos |

## 7.5 `memory_context_ref`

Campos mínimos:

| Campo | Obrigatório | Descrição |
|---|---|---|
| `memory_ref_id` | Sim | ID referência memória |
| `provider` | Sim | origem (ex.: mempalace) |
| `query_scope` | Sim | escopo da consulta |
| `window_start_utc` | Não | início da janela |
| `window_end_utc` | Não | fim da janela |
| `content_digest` | Sim | digest do contexto consultado |

---

## 8. Proposta de estrutura `src/intelligence/`

```text
src/intelligence/
├── __init__.py
├── domain.py                  # orquestração advisory e boundaries
├── guards.py                  # IntelligenceGuard + policy checks
├── profiles.py                # gating lite/standard/full
├── scenario_engine.py         # análise de cenário (determinística neste corte)
├── reasoning_advisor.py       # interface advisory (stub)
├── memory_bridge.py           # interface memória auxiliar (stub)
├── contracts.py               # contratos typed locais
└── serializers.py             # round-trip/compatibilidade de payloads
```

Notas:
- neste corte, módulos podem existir só como contrato/placeholder;
- integração externa real fica fora do escopo.

---

## 9. Integração com DECISION e LEARN

Regras:
- `DECISION` só pode consumir advisory através de `advisory_snapshot` explícito;
- `LEARN` só pode consumir advisory através de `advisory_snapshot` explícito;
- ausência de snapshot deve resultar em operação normal sem advisory, nunca em erro fatal;
- nenhum advisory pode alterar contrato base de `ExecutionIntent` ou fluxo de rollback.

---

## 10. Observabilidade e auditoria

Eventos/logs esperados:
- `advisory_request_received`
- `advisory_profile_gate_rejected`
- `advisory_response_emitted`
- `advisory_snapshot_frozen`

Campos mínimos de logging:
- `request_id`, `response_id`, `execution_profile`, `target_module`, `status`, `reason_code`.

---

## 11. Plano de testes (planeado)

### 11.1 Unit
- validação de contratos (`request/response/snapshot`);
- gating por profile (`lite/standard/full`);
- guardrails de operações proibidas.

### 11.2 Integration
- `DECISION` com/sem `advisory_snapshot`;
- `LEARN` com/sem `advisory_snapshot`;
- rejeição explícita em profile incompatível.

### 11.3 Contract
- round-trip de serialização dos contratos;
- compatibilidade backward/forward de payload.

### 11.4 Security / Boundary
- tentativa de alteração direta de `CORE`/`RISK`/`EXEC`/`RECOVERY` deve falhar;
- tentativa de limpeza de bloqueio via intelligence deve falhar;
- tentativa de execução de ordem via intelligence deve falhar.

---

## 12. Critérios de fecho deste corte

Este corte SDS-900 fica fechado quando:
- boundaries e contratos estiverem documentados;
- matriz de rastreabilidade incluir requisitos `INTELLIGENCE`;
- arquitetura futura no README refletir a nova camada;
- plano de testes inicial estiver definido.

---

## 13. Fora de escopo explícito

Fica fora deste corte:
- wiring OpenAI;
- conectores Telegram/XTB/MT5;
- agentes autônomos de execução;
- qualquer promoção de autoridade operacional da camada advisory.
