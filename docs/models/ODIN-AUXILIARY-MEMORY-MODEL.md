# ODIN-AUXILIARY-MEMORY-MODEL

**Versão:** 0.1  
**Estado:** Draft técnico inicial  
**Tipo de documento:** Modelo técnico transversal  
**Objetivo:** Definir o papel da memória auxiliar no Odin, incluindo fronteiras de autoridade, regras de ingestão, congelamento em snapshot e integração opcional com MemPalace.

---

## 1. Finalidade do documento

Este documento define a camada de **memória auxiliar** do Odin.

O objetivo é permitir que o sistema tenha melhor recall histórico, consulta assistida e suporte à aprendizagem sem contaminar a arquitetura autoritativa do runtime.

---

## 2. Princípio central

A memória auxiliar:
- **pode lembrar**
- **pode sugerir**
- **pode recuperar contexto histórico**

Mas:
- **não governa estado global**
- **não governa risco**
- **não governa execução**
- **não governa recovery**

---

## 3. Fronteiras de autoridade

| Camada | Papel |
|---|---|
| `CORE` | autoridade única de estado global |
| `SDS-110 / persistência crítica` | autoridade de snapshots, kill, bloqueios e markers de runtime |
| `RISK` | autoridade de envelopes e travões de risco |
| `EXEC` | autoridade do que foi ou não executado |
| `RECOVERY` | autoridade da reconstrução e confiança de retoma |
| memória auxiliar | contexto advisory e recall histórico |

---

## 4. Usos permitidos

- consulta assistida no DASH;
- recuperação de racional técnico anterior;
- recuperação de incidentes semelhantes;
- apoio advisory ao DECISION;
- suporte ao LEARN para análise e proposta;
- indexação de documentação, runbooks, testes, pós-mortems e decisões.

---

## 5. Usos proibidos

- calcular `global_state` oficial;
- limpar ou ativar `kill_switch`;
- calcular `active_block_vector` oficial;
- autorizar execução;
- substituir snapshots oficiais de decisão, risco, execução ou recovery;
- decidir sozinho promoção ou rollback.

---

## 6. Regra de congelamento

Se uma consulta à memória auxiliar influenciar um ciclo:

- no `DECISION`, o resultado efetivamente usado deve ser congelado no `decision_input_snapshot`;
- no `LEARN`, a evidência usada deve ser congelada no `learning_history_snapshot` ou na `change_proposal`;
- o racional final deve referir a existência dessa influência.

Sem congelamento, a memória auxiliar não pode influenciar um artefacto oficial.

---

## 7. Fontes de ingestão recomendadas

- `docs/**/*.md`
- relatórios de testes
- pós-mortems e incidentes
- resultados de shadow mode
- racionais de decisão consolidados
- resumos de recovery

---

## 8. Fontes a excluir

- ticks e feed bruto de alta frequência
- heartbeats contínuos
- estado transitório do CORE
- artefactos efémeros de `runtime/state/`
- dumps volumosos sem curadoria mínima

---

## 9. Integração recomendada com MemPalace

Para a fase inicial do Odin, o MemPalace deve ser tratado como:

- sidecar local opcional;
- provider de memória advisory;
- repositório semântico de longo prazo;
- ferramenta de apoio a operador, LEARN e DECISION.

Não deve entrar no caminho crítico do runtime autoritativo.

---

## 10. Falha e fallback

Se a memória auxiliar estiver indisponível:

- o DASH perde recall histórico avançado, mas mantém leitura oficial;
- o DECISION continua a decidir sem contexto advisory;
- o LEARN continua a usar histórico oficial persistido;
- o CORE, RISK, EXEC e RECOVERY não mudam de semântica.

---

## 11. Conclusão

O Odin pode ter memória sem ficar volátil.

A chave é simples:
- memória auxiliar para lembrar;
- snapshots oficiais para decidir;
- persistência crítica para governar.
