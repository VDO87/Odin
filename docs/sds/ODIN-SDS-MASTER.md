# ODIN-SDS-MASTER
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft técnico mestre  
**Tipo de documento:** Software Design Specification Master  
**Objetivo:** Consolidar a arquitetura documental técnica do Odin, ligar os SDS existentes, definir dependências, ordem de implementação, backlog técnico e regras de governação da fase de engenharia.

---

## 1. Finalidade do documento

O **ODIN-SDS-MASTER** é o documento-mãe da camada técnica do projeto Odin.

A sua função é transformar um conjunto de SDS individuais numa **estrutura de engenharia coerente**, com:

- visão técnica de conjunto;
- dependências entre módulos;
- ordem correta de implementação;
- ligação à rastreabilidade;
- backlog técnico por fase;
- critérios de prontidão para sair da documentação e entrar em código.

Sem este documento, os SDS existem, mas continuam dispersos.  
Com este documento, passam a fazer parte de um programa técnico organizado.

---

## 2. Âmbito

### 2.1 Incluído
Este documento inclui:
- lista e papel de cada SDS;
- arquitetura técnica macro do Odin;
- dependências entre módulos;
- ordem de implementação recomendada;
- backlog técnico por fase;
- ligação à matriz de rastreabilidade;
- critérios de prontidão técnica;
- riscos de engenharia já identificados.

### 2.2 Excluído
Este documento não inclui:
- implementação linha a linha;
- casos de teste completos;
- configuração final de deployment;
- detalhe matemático das estratégias;
- decisões finais de linguagem/framework.

---

## 3. Conjunto documental técnico atual

### 3.1 Documentos base

| Documento | Estado | Função |
|---|---|---|
| `ODIN_FSD_Consolidado_v0_5.md` | Existente | baseline funcional consolidada |
| `ODIN-CORE-STATE-AND-EVENT-MODEL.md` | Existente | modelo técnico canónico do CORE |
| `ODIN-TRACEABILITY-MATRIX.md` | Existente | rastreabilidade requisito -> SDS -> teste |

### 3.2 Documentos SDS existentes

| Documento | Estado | Função técnica principal |
|---|---|---|
| `SDS-100 — CORE` | Existente | arquitetura técnica do núcleo do sistema |
| `SDS-110 — CORE-PERSISTENCE` | Existente | persistência crítica do CORE |
| `SDS-120 — CORE-INTERFACES` | Existente | contratos do CORE com os restantes módulos |
| `SDS-200 — MARKET` | Existente | arquitetura técnica do módulo de mercado |
| `SDS-300 — DECISION` | Existente | motor técnico de decisão |
| `SDS-400 — RISK` | Existente | motor técnico de risco e travões |
| `SDS-500 — EXEC` | Existente | execução, confirmação e reconciliação |
| `SDS-600 — DASH` | Existente | dashboard técnico e supervisão humana |
| `SDS-700 — RECOVERY` | Existente | recuperação técnica e reconstrução de estado |
| `SDS-800 — LEARN` | Existente | evolução controlada, shadow e rollback |
| `SDS-900 — INTELLIGENCE-LAYER` | Existente | camada advisory de cenário, reasoning e memória auxiliar |

---

## 4. Visão técnica macro do sistema

### 4.1 Cadeia operacional principal

```text
MARKET -> DECISION -> EXEC
    \        ^         |
     \       |         v
      -> RISK --------> RECOVERY
             ^             ^
             |             |
             +---- CORE ---+
                    |
                    v
                   DASH
                    ^
                    |
                   LEARN
```

### 4.2 Leitura correta da arquitetura
- **CORE** é a autoridade de estado global e bloqueios.
- **MARKET** diz se o mercado é utilizável.
- **DECISION** decide com base em contexto e restrições.
- **RISK** limita o que pode ou não pode avançar.
- **EXEC** toca o mundo externo e confirma o que realmente aconteceu.
- **RECOVERY** trata incidentes e reconstrução de estado.
- **DASH** é a superfície operacional humana.
- **LEARN** melhora o sistema sem o desalinhar.

---

## 5. Papel técnico de cada SDS

### 5.1 CORE
**SDS-100 / 110 / 120**  
Fecham:
- máquina de estados;
- eventos e precedência;
- persistência crítica;
- interfaces centrais.

### 5.2 MARKET
**SDS-200**  
Fecha:
- qualidade/integridade do feed;
- sessões;
- spread adaptativo;
- contexto;
- prontidão para decisão.

### 5.3 DECISION
**SDS-300**  
Fecha:
- pipeline de avaliação;
- elegibilidade;
- scoring;
- confluência;
- intenção operacional.

### 5.4 RISK
**SDS-400**  
Fecha:
- limites;
- bloqueios;
- kill-switch;
- envelopes por modo.

### 5.5 EXEC
**SDS-500**  
Fecha:
- revalidação;
- submissão;
- confirmação;
- slippage;
- divergência.

### 5.6 DASH
**SDS-600**  
Fecha:
- projeção de estado;
- painéis;
- alarmes;
- permissões;
- controlo manual;
- logs e queries assistidas.

### 5.7 RECOVERY
**SDS-700**  
Fecha:
- incidentes;
- reconstrução;
- reconciliação;
- confiança;
- saída segura de recovery.

### 5.8 LEARN
**SDS-800**  
Fecha:
- análise de histórico;
- propostas;
- snapshots;
- shadow mode;
- promoção;
- rollback.

### 5.9 INTELLIGENCE LAYER
**SDS-900**  
Fecha:
- advisory de cenário (não autoritativo);
- advisory de reasoning (não autoritativo);
- bridge de memória auxiliar;
- contratos `advisory_request/response/snapshot`;
- gating por profile e boundaries de segurança.

---

## 6. Dependências técnicas entre SDS

| SDS | Depende principalmente de | Observações |
|---|---|---|
| SDS-100 CORE | FSD + CORE model | fundação do sistema |
| SDS-110 CORE-PERSISTENCE | SDS-100 | persistência do estado global |
| SDS-120 CORE-INTERFACES | SDS-100 | contratos centrais |
| SDS-200 MARKET | SDS-100, SDS-120 | publica prontidão/contexto |
| SDS-300 DECISION | SDS-100, 120, 200, 400, 500 | depende de mercado, risco e contrato de intenção |
| SDS-400 RISK | SDS-100, 120, 200 | depende do contexto e do estado |
| SDS-500 EXEC | SDS-100, 120, 300, 400 | depende de intenção, risco e estado |
| SDS-600 DASH | SDS-100, 120, 200, 300, 400, 500, 700, 800 | consome tudo, não governa o estado |
| SDS-700 RECOVERY | SDS-100, 110, 120, 200, 400, 500 | depende fortemente do estado persistido |
| SDS-800 LEARN | SDS-100, 300, 400, 600 | depende do contexto operacional e governação |
| SDS-900 INTELLIGENCE | SDS-100, 300, 600, 800 | advisory para DECISION/LEARN com snapshot congelado e sem autoridade operacional |

---

## 7. Ordem técnica recomendada para implementação

### 7.1 Fase 1 — Núcleo operacional
1. `SDS-100 — CORE`
2. `SDS-110 — CORE-PERSISTENCE`
3. `SDS-120 — CORE-INTERFACES`

### 7.2 Fase 2 — Consciência e controlo operacional
4. `SDS-200 — MARKET`
5. `SDS-400 — RISK`

### 7.3 Fase 3 — Inteligência decisória e execução
6. `SDS-300 — DECISION`
7. `SDS-500 — EXEC`

### 7.4 Fase 4 — Supervisão e resiliência
8. `SDS-600 — DASH`
9. `SDS-700 — RECOVERY`

### 7.5 Fase 5 — Evolução controlada
10. `SDS-800 — LEARN`

### 7.6 Regra importante
A ordem acima não é estética. É de engenharia.
Fazer DASH antes de CORE/RISK/EXEC seria erro estrutural.
Fazer LEARN antes de estabilizar DECISION/EXEC seria pior ainda.

---

## 8. Backlog técnico macro por fase

### 8.1 Fase 1 — Fundação técnica
**Objetivo:** ter um núcleo com estado, eventos, persistência e contratos mínimos

Entregáveis mínimos:
- state machine funcional;
- event queue/precedência;
- kill persistente;
- vetor de bloqueios;
- publishers de estado global;
- interfaces mínimas.

### 8.2 Fase 2 — Mercado e risco
**Objetivo:** impedir operação cega

Entregáveis mínimos:
- leitura e classificação do mercado;
- spread adaptativo;
- filtro de notícias;
- gating de risco;
- kill-switch funcional.

### 8.3 Fase 3 — Decidir e executar
**Objetivo:** fechar o pipeline ponta-a-ponta em demo

Entregáveis mínimos:
- ciclo decisório;
- intenção operacional com TTL;
- submissão simulada;
- confirmação/rejeição;
- tratamento de slippage e divergência.

### 8.4 Fase 4 — Operar com supervisão
**Objetivo:** tornar o sistema utilizável por humano e resiliente

Entregáveis mínimos:
- dashboard mínimo operacional;
- alarmes críticos;
- logs e queries;
- fluxo de recovery real;
- retoma segura.

### 8.5 Fase 5 — Evoluir com disciplina
**Objetivo:** permitir melhoria sem descontrolo

Entregáveis mínimos:
- snapshots;
- propostas formais;
- shadow mode;
- promoção;
- rollback.

---

## 9. Relação com a Traceability Matrix

### 9.1 Regra de governação
Nenhum desenvolvimento técnico relevante deve avançar sem ligação explícita à `ODIN-TRACEABILITY-MATRIX`.

### 9.2 Cadeia mínima obrigatória
Cada implementação deverá conseguir apontar para:
- `requirement_id`
- `source_document`
- `target_sds`
- `test_scope`
- `implementation_status`

### 9.3 Utilização prática
A matriz deve ser usada para:
- planeamento de sprints/fases;
- marcação de progresso;
- controlo de cobertura;
- identificação de requisitos órfãos;
- ligação entre documentação e código.

---

## 10. Critérios de prontidão para começar implementação real

O projeto só deve avançar para implementação séria quando, no mínimo:

1. o FSD v0.5 estiver congelado como baseline funcional;
2. o `ODIN-CORE-STATE-AND-EVENT-MODEL` estiver estável;
3. a `ODIN-TRACEABILITY-MATRIX` estiver atualizada;
4. os SDS do núcleo operacional estiverem revistos;
5. a ordem de implementação estiver assumida;
6. o repositório for estruturado em conformidade com os SDS;
7. existir política mínima de testes unitários e integração.

### Regra importante
Sem isto, começar a codificar é abrir dívida técnica logo na fundação.

---

## 11. Riscos de engenharia já identificados

| Risco | Impacto | Mitigação documental/técnica |
|---|---|---|
| Estado global mal serializado | Muito alto | SDS-100 + CORE model |
| Kill não persistente | Muito alto | SDS-110 |
| Interface sem contratos rígidos | Alto | SDS-120 |
| Mercado “vivo” mas inutilizável | Alto | SDS-200 |
| Decisão opaca ou não determinística | Alto | SDS-300 |
| Risco ignorado por timeout/silêncio | Muito alto | SDS-400 + CORE |
| Execução divergente não tratada | Muito alto | SDS-500 + SDS-700 |
| Dashboard a inventar lógica | Alto | SDS-600 |
| Recovery inconclusivo mas permissivo | Muito alto | SDS-700 |
| Aprendizagem sem rollback | Muito alto | SDS-800 |

---

## 12. Regras de governação da camada SDS

1. **SDS não contradiz FSD**  
   Se um SDS precisar de desviar funcionalmente, isso deve voltar ao FSD.

2. **Modelo canónico do CORE prevalece**  
   Estados, eventos e bloqueios do CORE devem obedecer ao `ODIN-CORE-STATE-AND-EVENT-MODEL`.

3. **Persistência crítica não é opcional**  
   Tudo o que afeta arranque seguro, kill e recovery deve ser tratado como infraestrutura obrigatória.

4. **Nenhum módulo decide sozinho sobre o estado global**  
   Só o CORE publica estado oficial.

5. **Todos os fluxos críticos devem ser testáveis**  
   Se um SDS não permite derivar testes mínimos, está incompleto.

6. **Shadow mode e rollback são obrigatórios antes de autonomia evolutiva séria**  
   LEARN sem shadow/rollback é risco, não melhoria.

---

## 13. Artefactos técnicos recomendados a seguir

Após o SDS-MASTER, os próximos artefactos úteis são:

### 13.1 Plano de testes técnico
Documento que traduza a traceability matrix em:
- unit tests
- integration tests
- fault injection
- recovery drills

### 13.2 Estrutura do repositório
Definição concreta de:
- diretórios
- boundaries por módulo
- shared libs
- runtime state
- logs
- config

### 13.3 Runbook técnico inicial
Para:
- arranque;
- shutdown;
- bloqueio manual;
- kill;
- recovery;
- manutenção.

### 13.4 Changelog técnico / roadmap
Para controlar:
- fases
- implementação
- desvios
- debt register

---

## 14. Critérios de aceitação do ODIN-SDS-MASTER

O ODIN-SDS-MASTER será considerado suficiente quando:

1. todos os SDS principais estiverem identificados e enquadrados;
2. as dependências entre SDS estiverem claras;
3. a ordem de implementação estiver definida;
4. o backlog técnico macro estiver organizado por fase;
5. a ligação à matriz de rastreabilidade estiver explícita;
6. os riscos principais de engenharia estiverem identificados;
7. o documento servir de guia real para passar da documentação ao repositório e ao código.

---

## 15. Conclusão

O **ODIN-SDS-MASTER** fecha a camada documental técnica de topo do projeto.

É ele que transforma:
- vários SDS bons,
em
- uma arquitetura documental de engenharia utilizável.

Sem este documento, os SDS continuam a existir como peças isoladas.  
Com este documento, passam a formar uma sequência de implementação coerente, com dependências, prioridades e critérios de prontidão.

Num projeto como o Odin, não basta ter bons documentos.  
É preciso que eles trabalhem uns com os outros com a mesma disciplina que se exige ao próprio sistema.
