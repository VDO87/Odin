# ODIN-RUNBOOK-v0.1
## Projeto Odin

**Versão:** 0.1  
**Estado:** Draft operacional inicial  
**Tipo de documento:** Runbook operacional  
**Objetivo:** Definir procedimentos operacionais mínimos para arranque, paragem, pausa, retoma, bloqueios, kill-switch, recovery, manutenção, exportação de logs e resposta humana a incidentes no Odin.

---

## 1. Finalidade do documento

O **ODIN-RUNBOOK-v0.1** existe para responder a uma necessidade simples e crítica:

**o que faz o operador, em termos práticos, quando o Odin está em cada situação relevante?**

A documentação FSD e SDS define:
- o que o sistema deve fazer;
- como os módulos devem ser desenhados;
- como devem ser testados.

Este runbook define:
- o que observar;
- o que verificar;
- o que fazer;
- o que nunca fazer;
- quando escalar;
- que artefactos recolher.

Sem este documento, o risco é alto:
- operador a agir por intuição;
- ações contraditórias em incidentes;
- reinícios precipitados;
- limpeza indevida de bloqueios;
- perda de evidência útil para diagnóstico.

---

## 2. Âmbito

### 2.1 Incluído
Este documento inclui procedimentos operacionais para:
- arranque do sistema;
- shutdown controlado;
- pausa e retoma;
- bloqueio manual;
- kill-switch;
- recovery;
- manutenção;
- exportação de logs;
- resposta a falhas típicas;
- recolha de evidência mínima.

### 2.2 Excluído
Este documento não inclui:
- detalhes profundos de debugging de código;
- procedimentos de infra distribuída futura;
- troubleshooting de broker específico além do necessário à operação;
- administração de segurança de sistema operativo.

---

## 3. Princípios operacionais

### 3.1 Não assumir normalidade
Se o sistema não mostrar claramente que está saudável, o operador deve assumir estado degradado ou bloqueado até prova em contrário.

### 3.2 Nunca limpar um bloqueio sem perceber a causa
Bloqueio resolvido por impulso é receita para falha repetida.

### 3.3 Recovery não é “dar restart”
Recovery é processo controlado. Reiniciar sem perceber o estado pode piorar a situação.

### 3.4 Kill tem precedência máxima
Quando o kill estiver ativo, a prioridade é segurança operacional, não continuidade.

### 3.5 Logs e evidência vêm antes de mexer demasiado
Em incidente sério, antes de alterar múltiplas coisas, o operador deve recolher o mínimo de evidência.

---

## 4. Estados operacionais que o operador deve conhecer

| Estado | Significado operacional |
|---|---|
| `ST-00 OFFLINE` | sistema desligado / sem ciclo ativo |
| `ST-10 STARTUP` | arranque e validação em curso |
| `ST-20 IDLE` | ativo mas sem operação em curso |
| `ST-30 MONITORING` | observação e validação de contexto |
| `ST-40 READY` | pronto para operar |
| `ST-50 ACTIVE` | operação ativa permitida |
| `ST-60 PAUSED` | suspensão temporária controlada |
| `ST-70 BLOCKED_RISK` | bloqueado por risco |
| `ST-80 BLOCKED_FAULT` | bloqueado por falha/integridade |
| `ST-90 ERROR` | erro não resolvido |
| `ST-100 RECOVERY` | reconstrução e validação de estado |
| `ST-110 TRAINING` | treino/aprendizagem |
| `ST-120 MAINTENANCE` | intervenção técnica controlada |

---

## 5. Check operacional rápido (pre-flight)

Antes de qualquer ação relevante, o operador deve confirmar no dashboard, no mínimo:

1. estado global atual;
2. modo atual;
3. profile de superfície ativa (`dashboard_profile`);
4. `execution_gate` em `operation_focus`;
5. resumo de `market_runtime` (`execution_profile`, `market_profile`, `instrument_scope`, `feed_scope`, `last_gate_status`);
6. motivo de rejeição do último gate de mercado, se existir (`last_rejection_reason`);
7. último registo de execução disponível (`last_execution`), quando existir;
8. motivo dominante de bloqueio, se existir;
9. vetor de bloqueios ativos;
10. kill ativo ou não;
11. estado do market;
12. estado do risco;
13. estado do exec;
14. estado do recovery;
15. existência de alarmes críticos ativos.
16. saúde dos providers de dados externos (`/api/external/status`) e aviso de fallback para demo.

### Regra obrigatória
Sem este check mínimo, não deve ser tomada ação crítica “às cegas”.

### 5.2 External Market Data v1
- `DemoProvider` é obrigatório e deve permanecer operacional mesmo sem internet.
- falha em `Alpha Vantage` ou `Trading Economics` não pode interromper operação do `CORE`.
- dados externos são auxiliares e não têm autoridade direta sobre `CORE`, `RISK` ou `EXEC`.
- em `profile=lite`, usar `DemoProvider` por defeito; `standard/full` podem ativar providers reais via configuração e segredos não versionados.
- quaisquer chaves de providers/IA expostas em chat devem ser tratadas como comprometidas (revogar e recriar fora de versionamento).

### 5.1 Nota de profile
- em `dashboard_profile=lite`, ações e queries LEARN não fazem parte da superfície operacional;
- tentativa de forçar ação LEARN em profile que a desativa deve resultar em `feature_disabled_for_profile`.

---

## 6. Procedimento de arranque normal

### 6.1 Quando usar
- após sistema estar `OFFLINE`
- após shutdown controlado
- após manutenção concluída
- em início normal de utilização

### 6.2 Pré-condições
- operador autorizado
- repositório/serviço local e configuração disponíveis
- sem kill persistente ativo conhecido
- sem manutenção em curso

### 6.2.1 Arranque local recomendado (corte Trader Console v1)
Num terminal para o CORE/estado local:

```bash
$HOME/odin-runtime/bin/start_odin.sh
```

Num segundo terminal para a consola visual:

```bash
$HOME/odin-runtime/bin/start_operator_console.sh
```

Aceder no browser:

```text
http://127.0.0.1:8080
```

Nota de operação para testes da consola:
- para testes API/UI da consola, usar preferencialmente apenas `start_operator_console.sh`;
- evitar correr `start_odin.sh` em paralelo durante este teste para não partilhar o mesmo `core_state.db`.

### 6.2.2 Leitura rápida da consola (Modo Operador)
No topo da consola, usar primeiro o **Modo Operador**:

1. Ler o diagnóstico automático.
2. Confirmar:
   - estado global;
   - se pode operar;
   - bloqueios ativos;
   - módulos indisponíveis/atrasados.
3. Ver a ação recomendada no próprio diagnóstico antes de emitir comandos.

Usar o **Modo Técnico** apenas quando for necessário analisar JSON completo dos endpoints.

Na vista cockpit:
- confirmar cartões críticos (`Estado`, `Saúde geral`, `Modo`, `Profile`, `Kill`, `Bloqueios`);
- validar diagnóstico automático e próxima ação recomendada;
- rever `Saúde dos módulos` e timeline de estado antes de comandos críticos;
- ajustar polling (`1s/2s/5s`) conforme carga e necessidade de observação.
- navegar por páginas específicas via menu/hash:
  - `#dashboard`, `#market`, `#risk`, `#decision`, `#execution`, `#portfolios`, `#logs`, `#config`, `#commands`
  - `#integrations` e `#intelligence` ficam como placeholders de evolução.

### 6.2.3 Política inicial de venues e carteiras
- `MT5` não é exclusivo de Forex por capacidade técnica, mas neste corte é o adapter preferencial para `FOREX` com foco `AUTO_DEMO` e execução curta.
- `XTB` é tratado como plataforma ampla para `ETF`/`STOCK`/`CFD` e carteiras `FIRE`/médio-longo prazo, inicialmente em workflow assistido (`TELEGRAM_ASSISTED`) ou confirmação humana.
- `Telegram` nunca executa ordens diretamente: toda a ação deve passar por `CommandGateway` e confirmação explícita.
- `XTB` com execução real permanece preparado, mas não ativo neste corte.
- decisões de `MEDIUM_TERM_3_5Y` e `FIRE_LONG_TERM` são advisory ou com confirmação humana.
- advisory de IA permanece não autoritativo no estado atual deste runbook.

### 6.2.4 Retoma de sessão
- para retoma rápida no dia seguinte, usar:
  - [`docs/runbooks/ODIN-SESSION-HANDOFF.md`](/home/vdo/Secretária/Projects_Codex/Odin_Teste/docs/runbooks/ODIN-SESSION-HANDOFF.md)

### 6.3 Passos
1. Confirmar que o sistema está efetivamente em `ST-00 OFFLINE`.
2. Verificar se não existe indicação externa de incidente não resolvido da sessão anterior.
3. Iniciar o processo de arranque pelo método oficial definido.
4. Observar transição para `ST-10 STARTUP`.
5. Confirmar:
   - leitura de estado persistido;
   - validação de kill flag;
   - health dos módulos críticos;
   - ausência de bloqueio de falha não resolvido.
6. Aguardar convergência para:
   - `ST-20 IDLE`, ou
   - `ST-30 MONITORING`, conforme política.

### 6.4 Critério de sucesso
- sistema não entra em erro ou bloqueio inesperado
- estado final coerente
- dashboard mostra informação consistente

### 6.5 Nunca fazer
- forçar modo `REAL` logo no arranque
- ignorar kill persistente
- assumir que “subiu” significa que está pronto

---

## 7. Procedimento de shutdown controlado

### 7.1 Quando usar
- paragem planeada
- manutenção
- fim de sessão operacional
- necessidade de reinício limpo

### 7.2 Passos
1. Confirmar estado atual e existência de operações pendentes.
2. Se necessário, fazer `PAUSE` antes de `STOP`.
3. Confirmar que não existem ações críticas intermédias em curso.
4. Emitir comando de `STOP` pelo caminho autorizado.
5. Aguardar:
   - fecho controlado de módulos;
   - escrita do estado persistido;
   - marcação de shutdown limpo.
6. Confirmar transição para `ST-00 OFFLINE`.

### 7.3 Critério de sucesso
- shutdown limpo registado
- sem perda de estado crítico
- sem falsos bloqueios no arranque seguinte

### 7.4 Nunca fazer
- matar processo abruptamente sem necessidade
- interromper persistência crítica
- desligar sistema operativo durante shutdown em curso

---

## 8. Procedimento de pausa

### 8.1 Quando usar
- suspensão temporária controlada
- necessidade de travar novas ações sem shutdown completo
- observação reforçada sem operar

### 8.2 Passos
1. Confirmar que o estado atual permite pausa.
2. Emitir `PAUSE` pelo dashboard ou canal oficial.
3. Confirmar transição para `ST-60 PAUSED`.
4. Verificar que:
   - novas intenções não avançam;
   - novas execuções não arrancam;
   - bloqueios e alarmes continuam visíveis.

### 8.3 Retoma a partir de pausa
1. Rever estado do sistema.
2. Confirmar ausência de kill e bloqueios impeditivos.
3. Emitir `RESUME`.
4. Confirmar regresso a `ST-30 MONITORING`, nunca diretamente a `ACTIVE`.

### 8.4 Nunca fazer
- usar `RESUME` sem rever o vetor de bloqueios
- tratar pausa como se fosse reset

---

## 9. Procedimento de bloqueio manual

### 9.1 Quando usar
- dúvida séria sobre o estado do sistema
- comportamento anómalo ainda não classificado
- necessidade humana explícita de travar o sistema
- operação não deve continuar até revisão

### 9.2 Passos
1. Confirmar motivo da ação.
2. Emitir bloqueio manual pelo canal autorizado.
3. Verificar que o bloqueio entra no vetor de bloqueios ativos.
4. Confirmar que o motivo dominante está coerente ou que o bloqueio manual fica visível mesmo que não seja dominante.
5. Registar razão operacional da ação.

### 9.3 Regras obrigatórias
- bloqueio manual não sai sozinho;
- recovery validado não limpa bloqueio manual;
- `RESUME` só pode ser usado após limpeza manual autorizada.

### 9.4 Nunca fazer
- limpar bloqueio manual sem explicar o motivo inicial
- esquecer que o bloqueio manual pode coexistir com outros

---

## 10. Procedimento de kill-switch

### 10.1 Quando usar
- condição crítica grave
- risco não controlado
- execução anómala séria
- incerteza incompatível com operação
- incidente que exija travagem máxima

### 10.2 Efeito esperado
- kill ativo
- bloqueio máximo compatível
- proibição de progressão operacional normal
- persistência do kill além de reboot

### 10.3 Passos do operador
1. Confirmar motivo crítico.
2. Acionar kill pelo mecanismo autorizado.
3. Confirmar:
   - kill ativo visível no DASH;
   - bloqueio persistido;
   - nenhuma nova progressão operacional normal possível.
4. Recolher evidência mínima do incidente.
5. Não tentar limpar o kill sem diagnóstico suficiente.

### 10.4 Limpeza do kill
Só pode ocorrer após:
- revisão técnica mínima;
- confirmação de causa;
- autorização adequada;
- registo auditável da limpeza.

### 10.5 Nunca fazer
- usar kill como substituto de pausa sem necessidade
- assumir que reboot limpa kill
- limpar kill por conveniência

---

## 11. Procedimento de entrada em manutenção

### 11.1 Quando usar
- intervenção técnica
- alterações de configuração
- validações técnicas
- inspeção operativa controlada

### 11.2 Passos
1. Confirmar necessidade real de manutenção.
2. Emitir comando de entrada em manutenção.
3. Escolher explicitamente perfil de manutenção:
   - `maintenance_soft`
   - `maintenance_managed_exit`
   - `maintenance_hard_exit`
4. Confirmar transição para `ST-120 MAINTENANCE`.
5. Verificar no dashboard o perfil ativo.

### 11.3 Regra obrigatória
Sem `maintenance_profile` explícito, a ação deve ser rejeitada com `maintenance_profile_required`.  
O operador deve reenviar o pedido com perfil explícito.

### 11.4 Nunca fazer
- entrar em manutenção sem saber o perfil aplicado
- assumir que manutenção limpa bloqueios críticos
- usar manutenção como bypass de kill ou bloqueio manual

---

## 12. Saída de manutenção

### 12.1 Passos
1. Confirmar que a intervenção técnica terminou.
2. Rever:
   - estado global
   - vetor de bloqueios
   - kill
   - health de módulos críticos
3. Emitir saída de manutenção pelo caminho autorizado.
4. Confirmar regresso a `ST-20 IDLE` ou estado compatível.

### 12.2 Regra obrigatória
A saída de manutenção não deve levar diretamente a `ACTIVE`.

---

## 13. Procedimento de recovery

### 13.1 Quando recovery deve ser esperado
- arranque após encerramento não limpo
- falha de energia
- divergência executória
- persistência inconsistente
- perda crítica de módulo
- incidente classificado como recuperável

### 13.2 O que o operador deve observar
- `ST-100 RECOVERY`
- tipo de incidente
- confiança da reconciliação
- resultado do recovery
- necessidade de intervenção humana
- bloqueios ainda ativos

### 13.3 Passos do operador durante recovery
1. Não forçar `RESUME` prematuramente.
2. Observar o tipo de incidente.
3. Confirmar se recovery está:
   - em curso;
   - validado;
   - validado com restrições;
   - inconclusivo;
   - falhado.
4. Se houver pedido de intervenção humana, parar e recolher evidência antes de atuar.

### 13.4 Saídas corretas do recovery
- `ST-20 IDLE`
- `ST-30 MONITORING`

### 13.5 Saída proibida
- `ST-50 ACTIVE` diretamente

### 13.6 Nunca fazer
- tratar recovery como simples restart
- limpar bloqueio manual durante recovery sem decisão humana explícita
- ignorar kill persistente

---

## 14. Recovery inconclusivo

### 14.1 Sinais típicos
- confiança baixa
- estado observado insuficiente
- persistência inconsistente
- divergência não resolvida
- intervenção humana requerida

### 14.2 Passos
1. Não tentar forçar progressão operacional.
2. Confirmar bloqueios ativos.
3. Exportar logs relevantes.
4. Recolher:
   - último estado conhecido
   - alarmes críticos
   - referências do incidente
5. Manter sistema bloqueado até diagnóstico suficiente.

### 14.3 Regra obrigatória
Recovery inconclusivo deve ser tratado como risco, não como atraso irritante.

---

## 15. Procedimento quando há divergência executória

### 15.1 Sinais típicos
- `EV-EXEC-DIVERGENCE`
- estado `divergence_active`
- discrepância entre intenção/submissão e estado observado

### 15.2 Passos
1. Parar tentativa de continuação normal.
2. Confirmar estado do EXEC.
3. Confirmar se o CORE já entrou em bloqueio ou recovery.
4. Recolher evidência:
   - `intent_id`
   - `decision_cycle_id`
   - estado executório
   - timestamps relevantes
5. Não assumir que “já passou”.

### 15.3 Regra obrigatória
Divergência séria deve ser tratada como incidente crítico.

---

## 16. Procedimento quando há intenção expirada

### 16.1 Sinais típicos
- `EV-INTENTION-EXPIRED`
- indicação no DASH de expiração antes da execução

### 16.2 Passos
1. Confirmar que não houve submissão indevida.
2. Verificar frequência do problema.
3. Recolher:
   - `intent_id`
   - `decision_cycle_id`
   - `created_at`
   - `expires_at`
   - motivo resumido
4. Tratar como sinal operacional útil, não como acidente fatal isolado.

### 16.3 Quando escalar
- se expirações forem repetitivas
- se ocorrerem em contexto que deveria ter baixa latência
- se estiverem a destruir eficácia operacional

---

## 17. Procedimento quando há rejeição por slippage

### 17.1 Sinais típicos
- `EV-EXEC-REJECTED-SLIPPAGE`
- alarme de desvio excessivo

### 17.2 Passos
1. Confirmar contexto de mercado na altura do evento.
2. Verificar:
   - spread
   - contexto macro
   - degradação de feed
   - latência
3. Recolher:
   - `intent_id`
   - `max_slippage`
   - desvio observado
4. Não tratar o evento como erro aleatório sem contexto.

---

## 18. Procedimento quando um módulo crítico perde heartbeat

### 18.1 Módulos críticos mínimos
- MARKET
- RISK
- EXEC

### 18.2 Passos
1. Confirmar qual o módulo com heartbeat em timeout.
2. Verificar se o CORE entrou em `ST-80 BLOCKED_FAULT`.
3. Confirmar se a perda é:
   - transitória;
   - persistente;
   - acompanhada de outros alarmes.
4. Se persistente:
   - manter bloqueio;
   - exportar logs;
   - preparar recovery ou manutenção.

### 18.3 Nunca fazer
- ignorar timeout porque “parece ter voltado”
- forçar `RESUME` sem confirmar estabilidade

---

## 19. Exportação de logs

### 19.1 Quando exportar
- incidente crítico
- recovery inconclusivo
- divergência
- slippage anómalo
- bloqueio persistente sem causa óbvia
- suporte a análise externa

### 19.2 Passos
1. Definir intervalo temporal relevante.
2. Selecionar módulos principais envolvidos.
3. Filtrar severidade, se necessário.
4. Executar exportação pelo DASH.
5. Confirmar sucesso da exportação.
6. Registar referência do ficheiro exportado.

### 19.3 Regra obrigatória
Exportação deve acontecer antes de mudanças excessivas no estado, sempre que possível.

---

## 20. Evidência mínima a recolher em incidente sério

Sempre que houver incidente sério, recolher no mínimo:
- timestamp aproximado
- estado global
- modo atual
- motivo dominante de bloqueio
- vetor de bloqueios ativos
- kill ativo ou não
- estado de MARKET
- estado de RISK
- estado de EXEC
- estado de RECOVERY
- IDs relevantes (`intent_id`, `decision_cycle_id`, `recovery_id`, etc.)
- referência dos logs exportados

---

## 21. O que nunca fazer

1. Não limpar bloqueios sem perceber a causa.
2. Não assumir que restart resolve tudo.
3. Não ignorar kill persistente.
4. Não tratar dashboard degradado como prova de sistema saudável.
5. Não forçar `RESUME` durante ou após recovery inconclusivo.
6. Não entrar em modo real sem confirmação explícita.
7. Não ativar manutenção sem saber o perfil.
8. Não avançar após divergência executória como se nada tivesse acontecido.

---

## 22. Escalada mínima

O operador deve escalar quando existir:
- recovery inconclusivo;
- divergência não explicada;
- kill ativo sem clareza de causa;
- persistência inconsistente;
- perda repetida de heartbeat em módulo crítico;
- slippage ou expiração anormalmente frequentes;
- comportamento contraditório entre módulos.

---

## 23. Checklist rápido por situação

### 23.1 Antes de `RESUME`
- [ ] kill inativo
- [ ] sem bloqueio manual por limpar
- [ ] sem bloqueio de falha ativo
- [ ] recovery fechado com saída segura
- [ ] health dos módulos críticos aceitável

### 23.2 Antes de limpar kill
- [ ] causa identificada
- [ ] logs recolhidos
- [ ] estado coerente
- [ ] autorização adequada
- [ ] limpeza auditável

### 23.3 Antes de sair de manutenção
- [ ] perfil de manutenção conhecido
- [ ] intervenção concluída
- [ ] sem novos bloqueios críticos
- [ ] estado do CORE coerente
- [ ] sem tentativa de salto direto para `ACTIVE`

---

## 24. Artefactos a usar em conjunto com este runbook

Este documento deve ser usado juntamente com:
- `ODIN_FSD_Consolidado_v0_5.md`
- `ODIN-TRACEABILITY-MATRIX.md`
- `ODIN-SDS-MASTER.md`
- `ODIN-IMPLEMENTATION-ROADMAP.md`
- `ODIN-TEST-PLAN.md`

---

## 25. Critérios de aceitação do ODIN-RUNBOOK-v0.1

Este runbook será considerado suficiente quando:
1. o operador souber o que fazer em arranque, shutdown, pausa e retoma;
2. bloqueio manual, kill e recovery tiverem procedimentos claros;
3. incidentes críticos tiverem resposta mínima definida;
4. exportação de logs e recolha de evidência estiverem formalizadas;
5. o documento reduzir ações impulsivas e contraditórias em incidentes.

---

## 26. Conclusão

O **ODIN-RUNBOOK-v0.1** fecha a camada operacional humana mínima do projeto.

Sem ele, o Odin pode estar muito bem desenhado no papel e no código, mas continua vulnerável ao momento em que alguém precisa de intervir de forma rápida e disciplinada.

Com ele, o projeto ganha:
- procedimentos mínimos;
- linguagem operacional comum;
- resposta menos impulsiva a incidentes;
- melhor recolha de evidência;
- maior coerência entre sistema e operador.

Num sistema como o Odin, operar bem não depende só do software. Depende também de o humano não fazer disparates quando a pressão sobe.
