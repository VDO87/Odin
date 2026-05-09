# SDS-400 — RISK
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Software Design Specification  
**Domínio:** Arquitetura técnica do módulo RISK, envelopes operacionais, limites, bloqueios, kill-switch persistente, cooldowns, classificação de permissão e integração com CORE, MARKET, DECISION, EXEC e DASH.

---

## 1. Finalidade do documento

Este documento define a especificação técnica do módulo **RISK** do Odin.

Se o FSD-400 define **o que o módulo de risco deve impor**, este SDS-400 define **como o módulo deverá ser construído** para:
- avaliar permissões de operação;
- impor limites por operação, período e contexto;
- classificar o risco em allow/restrict/block/kill;
- manter kill-switch persistente;
- suportar cooldowns e desbloqueios controlados;
- publicar o seu estado técnico e funcional ao CORE e aos restantes módulos críticos.

O módulo RISK não escolhe a tática nem executa ordens. O seu papel técnico é atuar como **camada de proteção determinística**, impedindo que o Odin opere fora do envelope autorizado.

---

## 2. Âmbito técnico

### 2.1 Incluído
Este documento inclui:
- arquitetura lógica do módulo RISK;
- modelo técnico de envelopes e limites;
- cálculo técnico de estado de risco;
- gestão de kill-switch persistente;
- modelo de cooldown;
- desbloqueios e reentrada controlada;
- interface com CORE, MARKET, DECISION, EXEC e DASH;
- persistência mínima de kill e snapshots de risco;
- eventos publicados pelo módulo;
- timeouts, fail-safe e testes técnicos mínimos.

### 2.2 Excluído
Este documento não inclui:
- scoring do DECISION;
- modelo técnico do broker;
- gestão detalhada de posição em mercado;
- UI detalhada do DASH;
- algoritmos avançados de otimização de risco tipo portefólio multi-ativo.

---

## 3. Objetivos técnicos

O módulo RISK deverá garantir, no mínimo:

1. **Envelope operacional formal**
   A operação deve ser classificada de forma determinística em allow/restrict/block/kill.

2. **Proteção multicamada**
   O risco deve resultar de limites por operação, período, frequência, sequência negativa e contexto de mercado.

3. **Kill persistente**
   O kill-switch deve sobreviver a reboot e impedir operação até limpeza autorizada.

4. **Desbloqueio controlado**
   O regresso de bloqueio para estado operacional deve ser condicionado e auditável.

5. **Fail-safe**
   Se o módulo não conseguir avaliar com confiança suficiente, o resultado por defeito deve ser conservador.

6. **Integração forte**
   O RISK deve ser consumível por CORE, DECISION, EXEC e DASH sem semântica ambígua.

---

## 4. Requisitos de origem

Este SDS deriva principalmente de:
- FSD-400 — RISK
- FSD consolidado v0.5
- SDS-100 — CORE
- SDS-110 — CORE-PERSISTENCE
- SDS-120 — CORE-INTERFACES
- SDS-200 — MARKET
- ODIN-CORE-STATE-AND-EVENT-MODEL
- ODIN-TRACEABILITY-MATRIX

### 4.1 Mapeamento macro

| Requisito funcional | Origem | Resposta técnica neste SDS |
|---|---|---|
| Bloquear por limites críticos | FSD-400 | `RiskStateEngine` + `LimitEvaluator` |
| Distinguir allow/restrict/block/kill | FSD-400 | `RiskDecisionClassifier` |
| Kill persistente deve sobreviver a reboot | FSD-400 / v0.4 / v0.5 | `KillSwitchManager` + persistência |
| Bloqueio manual não pode ser limpo automaticamente | v0.3 / v0.5 | integração com `BlockManager` do CORE |
| Contexto hostil deve reduzir envelope | FSD-400 + SDS-200 | `ContextPenaltyEvaluator` |
| Cooldown após perda/risco | FSD-400 | `CooldownManager` |

---

## 5. Arquitetura lógica do RISK

O módulo RISK deverá ser decomposto, no mínimo, nos seguintes componentes técnicos:

| Componente | Responsabilidade técnica |
|---|---|
| `RiskOrchestrator` | coordenação central do módulo |
| `RiskStateEngine` | cálculo do estado de risco atual |
| `LimitEvaluator` | avaliação de limites por operação e agregados |
| `ExposureEvaluator` | avaliação de exposição simultânea |
| `FrequencyEvaluator` | avaliação de cadência operacional |
| `SequenceLossEvaluator` | avaliação de perdas consecutivas / degradação |
| `ContextPenaltyEvaluator` | penalização por contexto vindo do MARKET |
| `CooldownManager` | gestão de cooldowns e reentrada |
| `KillSwitchManager` | gestão de kill ativo, persistência e limpeza |
| `RiskDecisionClassifier` | classificação em allow/restrict/block/kill |
| `RiskStatePublisher` | publicação de estado/eventos |
| `RiskSnapshotStore` | persistência mínima de snapshots relevantes |
| `RiskAuditLogger` | logging técnico do módulo |

---

## 6. Modelo técnico de decisão de risco

### 6.1 Saídas canónicas do módulo
O módulo RISK deverá convergir para uma destas saídas lógicas:

| Código lógico | Significado |
|---|---|
| `ALLOW` | operação permitida |
| `RESTRICT` | operação permitida com limitações adicionais |
| `BLOCK` | nova operação proibida |
| `KILL` | travão máximo ativo |

### 6.2 Estados internos canónicos (`RS-*`)

| Código | Nome técnico | Significado |
|---|---|---|
| RS-10 | NORMAL | risco dentro do envelope |
| RS-20 | RESTRICTED | envelope reduzido |
| RS-30 | BLOCKED | nova operação não permitida |
| RS-40 | KILL_ACTIVE | kill-switch ativo |
| RS-50 | DEGRADED | risco condicionado por perda de confiança/contexto |

### 6.3 Regra obrigatória
O estado interno do RISK e a saída lógica não podem divergir semanticamente.  
Exemplo:
- `RS-40` implica `KILL`
- `RS-30` implica `BLOCK`

---

## 7. Entradas técnicas do RISK

O módulo RISK deverá consumir, no mínimo:

### 7.1 Do CORE
- `global_state`
- `current_mode`
- `active_block_vector` relevante
- permissões globais de operação

### 7.2 Do MARKET
- `market_state`
- `context_state`
- `readiness_state`
- `spread_state`
- `news_guard_active`
- sinais de degradação/hostilidade

### 7.3 Do DECISION
- intenção de nova operação;
- `decision_cycle_id`
- `intent_id`, quando aplicável;
- identificação da tática;
- referência temporal;
- impacto esperado em exposição, quando disponível.

### 7.4 Do EXEC / histórico operacional
- execuções confirmadas;
- rejeições relevantes;
- perdas/lucros realizados;
- slippage crítico, se for usado como penalizador;
- divergências executórias, quando afetarem envelope.

### 7.5 Da configuração ativa
- limites por operação;
- limites por período;
- cooldowns;
- thresholds de sequência negativa;
- regras de penalização por contexto;
- política de kill.

---

## 8. Modelo técnico de configuração de risco

### 8.1 Estrutura mínima: `risk_policy_config`

| Campo | Obrigatório | Descrição |
|---|---|---|
| `policy_id` | Sim | ID da política |
| `policy_version` | Sim | versão da política |
| `mode_scope` | Sim | modo(s) a que se aplica |
| `max_risk_per_operation` | Sim | limite por operação |
| `max_daily_loss` | Sim | perda diária máxima |
| `max_weekly_loss` | Recomendado | perda semanal máxima |
| `max_open_positions` | Sim | exposição simultânea máxima |
| `max_ops_per_window` | Sim | máximo de operações por janela |
| `cooldown_after_loss_ms` | Recomendado | cooldown após perda |
| `max_consecutive_losses` | Recomendado | perdas consecutivas máximas |
| `context_hostile_action` | Sim | ação em contexto hostil |
| `kill_policy` | Sim | política de kill |
| `auto_unblock_allowed` | Sim | se desbloqueio automático é permitido |

### 8.2 Regra obrigatória
O RISK não deve operar sem política de risco ativa válida para o modo atual.

---

## 9. Categorias técnicas de risco

### 9.1 Risco por operação
Avalia se uma nova intenção ultrapassa o envelope máximo por entrada.

### 9.2 Risco agregado diário / semanal
Avalia impacto acumulado em janelas temporais configuradas.

### 9.3 Risco por exposição simultânea
Avalia número e peso relativo de posições/operações abertas ou ativas.

### 9.4 Risco por frequência
Avalia excesso de cadência operacional.

### 9.5 Risco por sequência negativa
Avalia perdas consecutivas ou degradação persistente.

### 9.6 Risco contextual
Avalia penalização por `MC-*`, spread hostil, news guard ou feed degradado.

### 9.7 Risco sistémico
Avalia condições que justifiquem kill ou bloqueio forte:
- divergência crítica;
- incoerência persistente;
- kill já ativo;
- integridade insuficiente para operar.

---

## 10. Avaliador de limites por operação

### 10.1 Objetivo
Determinar se a intenção proposta cabe no envelope por entrada.

### 10.2 Entradas mínimas
- `intent_id`
- `decision_cycle_id`
- `max_risk_per_operation`
- impacto esperado da operação
- `current_mode`

### 10.3 Resultado lógico mínimo
- `OP_LIMIT_OK`
- `OP_LIMIT_RESTRICTED`
- `OP_LIMIT_EXCEEDED`

### 10.4 Regras obrigatórias
- operação acima do limite máximo não pode resultar em `ALLOW`.
- modos mais agressivos/menos conservadores não podem existir sem configuração explícita.
- em modo `REAL`, o limite por operação deve ser tratado com a política mais conservadora.

---

## 11. Avaliador de risco agregado

### 11.1 Objetivo
Evitar dano acumulado por múltiplas operações individualmente “válidas”.

### 11.2 Métricas mínimas
- `daily_realized_pnl`
- `weekly_realized_pnl`
- `ops_count_window`
- `loss_streak_count`

### 11.3 Thresholds mínimos parametrizáveis
- `max_daily_loss`
- `max_weekly_loss`
- `max_ops_per_window`
- `max_consecutive_losses`

### 11.4 Regras obrigatórias
- ao atingir `max_daily_loss`, o módulo deve convergir pelo menos para `BLOCK`;
- ao atingir limiar extremo definido pela política, pode convergir para `KILL`;
- o RISK deve distinguir restrição progressiva de bloqueio total.

---

## 12. Avaliador de exposição simultânea

### 12.1 Objetivo
Evitar sobrecarga por múltiplas posições ou intenções concorrentes.

### 12.2 Métricas mínimas
- `open_positions_count`
- `pending_intents_count`
- `gross_exposure`
- `net_directional_exposure`, quando aplicável

### 12.3 Regras obrigatórias
- se `open_positions_count >= max_open_positions`, nova entrada não pode resultar em `ALLOW`;
- exposição combinada pode justificar `RESTRICT` mesmo antes do bloqueio total;
- a integração final com posição real poderá ser refinada no SDS do EXEC, mas o RISK deve prever o conceito.

---

## 13. Avaliador de frequência operacional

### 13.1 Objetivo
Impedir sobreoperação.

### 13.2 Métricas mínimas
- número de operações por janela;
- intervalo desde a última operação;
- intervalo desde a última perda.

### 13.3 Regras obrigatórias
- excesso de cadência deve resultar em `RESTRICT` ou `BLOCK`, conforme política;
- após perda relevante, pode aplicar-se cooldown obrigatório.

---

## 14. Avaliador de sequência negativa

### 14.1 Objetivo
Travar insistência operacional após degradação persistente.

### 14.2 Métricas mínimas
- `loss_streak_count`
- `recent_win_rate`, se aplicável
- `recent_strategy_degradation_flag`

### 14.3 Regras obrigatórias
- atingir `max_consecutive_losses` deve provocar no mínimo `BLOCK`;
- a política pode permitir degradação progressiva antes do bloqueio total;
- o RISK não pode aumentar envelope para “recuperar perdas”.

---

## 15. Penalização contextual

### 15.1 Objetivo
Reduzir permissividade em contexto hostil/sensível.

### 15.2 Entradas mínimas do MARKET
- `market_state`
- `context_state`
- `spread_state`
- `news_guard_active`
- `readiness_state`

### 15.3 Regras mínimas
- `MC-30` deve poder conduzir a `RESTRICT`;
- `MC-40` deve poder conduzir a `BLOCK`;
- `MC-50` não pode ser tratado como normalidade;
- `MS-20` pode reduzir envelope mesmo sem bloqueio completo;
- `news_guard_active=true` deve poder impedir operação real por política.

---

## 16. Cooldown manager

### 16.1 Objetivo
Impor tempos mínimos de espera antes de nova tentativa operacional.

### 16.2 Estrutura mínima de cooldown

| Campo | Obrigatório |
|---|---|
| `cooldown_id` | Sim |
| `cooldown_reason` | Sim |
| `started_at_utc` | Sim |
| `expires_at_utc` | Sim |
| `scope` | Sim |
| `manual_clear_required` | Recomendado |

### 16.3 Tipos mínimos de cooldown
- `after_loss`
- `after_block`
- `after_recovery`
- `after_manual_intervention`

### 16.4 Regras obrigatórias
- cooldown ativo impede `ALLOW` pleno;
- expiração do cooldown não limpa automaticamente bloqueios de precedência superior;
- cooldown é condição de desbloqueio, não desbloqueio por si só.

---

## 17. KillSwitch manager

### 17.1 Objetivo
Gerir o travão máximo do módulo RISK.

### 17.2 Condições mínimas de ativação
A política deve suportar, no mínimo:
- perda crítica extrema;
- comando manual autorizado;
- divergência grave combinada com risco sistémico;
- violação crítica de envelope configurado;
- política definida pelo operador.

### 17.3 Estrutura mínima do kill

| Campo | Obrigatório |
|---|---|
| `kill_id` | Sim |
| `is_active` | Sim |
| `activated_at_utc` | Sim |
| `source_module` | Sim |
| `reason_code` | Sim |
| `reason_text` | Recomendado |
| `manual_clear_required` | Sim |
| `persisted_ref` | Recomendado |

### 17.4 Regras obrigatórias
- kill ativo implica `RS-40` e saída lógica `KILL`;
- kill deve ser persistido fora da memória volátil;
- reboot não limpa kill;
- limpeza de kill exige ação autorizada e auditável;
- recovery validado não limpa kill automaticamente.

---

## 18. Classificador de decisão de risco

### 18.1 Objetivo
Combinar resultados parciais dos avaliadores num estado final de risco.

### 18.2 Regra de precedência interna
Da maior para a menor:
1. `KILL`
2. `BLOCK`
3. `RESTRICT`
4. `ALLOW`

### 18.3 Regras obrigatórias
- se qualquer avaliador crítico devolver condição de kill, o resultado final deve ser `KILL`;
- se não houver kill mas existir bloqueio crítico, o resultado final deve ser `BLOCK`;
- `ALLOW` só é possível se nenhum avaliador produzir bloqueio, kill ou restrição impeditiva;
- falha interna do RISK em avaliar com confiança suficiente deve tender para `BLOCK`.

---

## 19. Persistência mínima do RISK

### 19.1 Objetivo
Preservar memória mínima relevante de risco, sobretudo kill e snapshots úteis de envelope.

### 19.2 Itens mínimos a persistir
- kill-switch ativo/inativo;
- último snapshot de risco relevante;
- cooldowns ativos;
- referência à política de risco ativa;
- timestamp do último cálculo consistente.

### 19.3 Estrutura mínima de `risk_snapshot`

| Campo | Obrigatório |
|---|---|
| `risk_snapshot_id` | Sim |
| `created_at_utc` | Sim |
| `risk_state` | Sim |
| `risk_decision` | Sim |
| `dominant_risk_reason` | Sim |
| `policy_id` | Sim |
| `cooldowns_active` | Recomendado |
| `kill_active` | Sim |
| `context_penalty_state` | Recomendado |

### 19.4 Regras obrigatórias
- snapshot de risco não substitui a persistência canónica do CORE;
- kill persistente deve ser coerente com o snapshot de risco e com a persistência do CORE.

---

## 20. Eventos publicados pelo RISK

### 20.1 Eventos mínimos
- `EV-RISK-ALLOW`
- `EV-RISK-RESTRICT`
- `EV-RISK-BLOCK`
- `EV-KILL-ACTIVE`
- `EV-KILL-CLEARED`
- `risk_cooldown_started`
- `risk_cooldown_expired`
- `EV-HB-OK`

### 20.2 Regras obrigatórias
- mudança real do estado de risco deve ser publicável;
- kill ativo deve gerar evento crítico inequívoco;
- limpeza de kill deve gerar evento auditável e não silencioso.

---

## 21. Interface com CORE

### 21.1 O CORE consome do RISK
- `risk_state`
- `risk_decision`
- `kill_active`
- `dominant_risk_reason`
- heartbeat

### 21.2 Payload mínimo publicado ao CORE

| Campo | Obrigatório |
|---|---|
| `risk_state` | Sim |
| `risk_decision` | Sim |
| `kill_active` | Sim |
| `dominant_risk_reason` | Sim |
| `risk_snapshot_ref` | Recomendado |
| `cooldown_active` | Recomendado |

### 21.3 Regras obrigatórias
- o CORE não deve precisar de recalcular risco a partir de métricas brutas;
- `EV-KILL-ACTIVE` tem precedência máxima sobre operação;
- `EV-KILL-CLEARED` não implica desbloqueio automático do sistema.

---

## 22. Interface com MARKET

### 22.1 O RISK consome do MARKET
- `market_state`
- `context_state`
- `readiness_state`
- `spread_state`
- `news_guard_active`

### 22.2 Regras obrigatórias
- o MARKET informa o contexto; o RISK decide a penalização;
- `MC-40` e/ou news guard crítico devem poder restringir ou bloquear operação real.

---

## 23. Interface com DECISION

### 23.1 O RISK consome do DECISION
- `intent_id`
- `decision_cycle_id`
- impacto esperado da operação;
- referência temporal;
- tática candidata;
- `max_slippage`, quando relevante à política.

### 23.2 O DECISION consome do RISK
- saída `ALLOW/RESTRICT/BLOCK/KILL`
- motivo dominante
- estado resumido

### 23.3 Regras obrigatórias
- o DECISION não deve tentar contornar `BLOCK` ou `KILL`;
- `RESTRICT` deve ser interpretado como oportunidade condicionada, não permissão plena.

---

## 24. Interface com EXEC

### 24.1 O EXEC consome do RISK
- envelope atual;
- `risk_decision`;
- kill ativo;
- cooldown impeditivo;
- restrições adicionais de execução.

### 24.2 O RISK consome do EXEC
- resultado executório relevante;
- rejeição por slippage;
- divergência;
- resultados necessários ao cálculo de perdas/ganhos e sequência negativa.

### 24.3 Regras obrigatórias
- o EXEC não deve iniciar nova submissão se o RISK não estiver permissivo;
- eventos do EXEC que alterem perfil de risco devem atualizar o RISK com baixa latência.

---

## 25. Interface com DASH

### 25.1 O DASH consome do RISK
- `risk_state`
- `risk_decision`
- motivo dominante
- kill ativo
- cooldowns ativos
- limites resumidos relevantes

### 25.2 O DASH poderá emitir ao RISK, via CORE ou fluxo autorizado
- pedido de kill manual;
- pedido de limpeza autorizada de kill;
- consulta de detalhe de risco.

### 25.3 Regras obrigatórias
- o DASH deve conseguir mostrar claramente `RESTRICT` vs `BLOCK` vs `KILL`;
- kill ativo deve ser impossível de confundir com bloqueio comum.

---

## 26. Heartbeat do módulo RISK

### 26.1 Objetivo
Permitir ao CORE distinguir RISK saudável de RISK silencioso ou encravado.

### 26.2 Payload mínimo do heartbeat

| Campo | Obrigatório |
|---|---|
| `module_id` | Sim |
| `timestamp_utc` | Sim |
| `risk_state` | Sim |
| `risk_decision` | Sim |
| `kill_active` | Sim |
| `health_flag` | Sim |

### 26.3 Regras obrigatórias
- heartbeat deve ser periódico e parametrizável;
- RISK vivo mas incapaz de avaliar com confiança deve refletir isso em estado/health;
- silêncio do RISK não pode ser interpretado como `ALLOW`.

---

## 27. Logging técnico do RISK

### 27.1 Campos mínimos
- `timestamp_utc`
- `policy_id`
- `risk_state`
- `risk_decision`
- `dominant_risk_reason`
- `kill_active`
- `cooldown_state`
- `context_penalty_state`
- `severity`
- `message`

### 27.2 Eventos obrigatórios a logar
- ativação de bloqueio por risco;
- ativação de kill;
- limpeza de kill;
- início/fim de cooldown;
- alteração de política ativa;
- falha interna de avaliação;
- transição `ALLOW -> RESTRICT/BLOCK/KILL`;
- transição `BLOCK -> RESTRICT/ALLOW` quando aplicável.

---

## 28. Timeouts e fail-safe

### 28.1 Timeouts mínimos parametrizáveis

| Parâmetro | Função |
|---|---|
| `risk_heartbeat_interval_ms` | intervalo do heartbeat |
| `risk_heartbeat_timeout_ms` | timeout de liveness |
| `risk_eval_timeout_ms` | timeout máximo para avaliação de risco |
| `risk_policy_load_timeout_ms` | timeout de carregamento de política |

### 28.2 Regras obrigatórias
- se o RISK não conseguir avaliar em tempo útil, o fallback deve ser conservador;
- `risk_eval_timeout_ms` excedido não pode resultar implicitamente em `ALLOW`;
- falha grave do RISK deve refletir-se em bloqueio/estado seguro via CORE.

---

## 29. Erros de contrato e erro interno

### 29.1 Tipos mínimos
- `risk_invalid_policy_config`
- `risk_missing_required_metric`
- `risk_schema_version_mismatch`
- `risk_eval_timeout`
- `risk_internal_evaluation_error`
- `risk_inconsistent_kill_state`

### 29.2 Regras obrigatórias
- política inválida impede operação normal;
- inconsistência de kill deve ser tratada como severidade crítica;
- erro repetido de avaliação pode conduzir a bloqueio sistémico.

---

## 30. Testes técnicos mínimos

### 30.1 Unit tests
- classificação `ALLOW/RESTRICT/BLOCK/KILL`;
- ativação de cooldown;
- precedência interna do classificador;
- persistência de kill;
- penalização por contexto hostil;
- validação de política.

### 30.2 Integration tests
- operação permitida com envelope normal;
- contexto hostil força `RESTRICT` ou `BLOCK`;
- perda diária máxima força `BLOCK`;
- kill manual persiste após reboot;
- `EV-KILL-CLEARED` não desbloqueia sistema sem validação global;
- cooldown ativo impede nova operação.

### 30.3 Fault-injection tests
- política inválida;
- timeout de avaliação;
- RISK sem heartbeat;
- kill ativo incoerente com persistência;
- divergência executória acompanhada de risco sistémico.

---

## 31. Critérios de aceitação

O SDS-400 — RISK será considerado tecnicamente suficiente quando:

1. a arquitetura do módulo suportar avaliação multicamada de risco;
2. `ALLOW/RESTRICT/BLOCK/KILL` estiverem tecnicamente definidos;
3. kill persistente estiver formalizado;
4. cooldowns e desbloqueios condicionados estiverem definidos;
5. o RISK puder ser consumido pelo CORE, DECISION, EXEC e DASH sem ambiguidade;
6. o módulo tiver fail-safe claro em caso de erro ou timeout;
7. o documento permitir implementação e testes diretos.

---

## 32. Dependências e próximos documentos

### 32.1 Dependências principais
- SDS-100 — CORE
- SDS-110 — CORE-PERSISTENCE
- SDS-120 — CORE-INTERFACES
- SDS-200 — MARKET
- ODIN-CORE-STATE-AND-EVENT-MODEL
- ODIN-TRACEABILITY-MATRIX

### 32.2 Próximos documentos recomendados
1. **SDS-500 — EXEC**
2. **SDS-300 — DECISION**
3. **SDS-600 — DASH**
4. **SDS-700 — RECOVERY**

---

## 33. Conclusão

O SDS-400 transforma o RISK num componente técnico de proteção real, e não apenas num conjunto vago de limites.

Sem este documento, o Odin corre o risco de ter regras de risco dispersas, desbloqueios ambíguos, kill volátil e falhas perigosas de semântica entre contexto, decisão e execução.

Com este documento, o RISK passa a ter:
- motor de envelope técnico;
- kill persistente;
- cooldowns formais;
- integração estável com o CORE;
- capacidade de falhar de forma segura.

Num sistema deste tipo, risco mal implementado não é defeito de detalhe. É falha estrutural.
