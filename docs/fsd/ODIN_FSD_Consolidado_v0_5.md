# ODIN — FSD CONSOLIDADO v0.5

**Estado:** Draft consolidado  
**Objetivo:** Consolidar num único ficheiro Markdown o pacote FSD do Projeto Odin, incluindo FSD Master, FSD por módulo, casos de uso e Matriz Mestra.

---

## Índice
- FSD-000 — MASTER
- FSD-100 — CORE
- FSD-200 — MARKET
- FSD-300 — DECISION
- FSD-400 — RISK
- FSD-500 — EXEC
- FSD-600 — DASH
- FSD-700 — RECOVERY
- FSD-800 — LEARN
- FSD-900 — USE CASES
- ODIN — MATRIZ MESTRA

---

# FSD-000 — MASTER

## Objetivo do sistema
O Odin é um sistema modular de análise, decisão, supervisão, execução controlada e aprendizagem operacional aplicado a investimento automatizado, com foco inicial em Forex.

O sistema deverá ser capaz de:
- observar e interpretar o estado do mercado;
- integrar contexto operacional relevante;
- avaliar táticas e condições de entrada;
- decidir se pode ou não operar;
- executar ações autorizadas dentro de limites definidos;
- bloquear comportamento inseguro;
- registar integralmente decisões, eventos, erros e resultados;
- apresentar o seu estado e histórico ao utilizador;
- evoluir por aprendizagem controlada, sem comprometer a rastreabilidade.

## Âmbito funcional
### Incluído
- gestão do estado global do sistema;
- ingestão e validação de dados de mercado;
- avaliação de contexto de mercado e contexto operacional;
- classificação e pontuação de táticas/estratégias;
- decisão de permissão, rejeição, espera ou bloqueio;
- execução controlada de ordens em ambiente autorizado;
- gestão de risco por regras e limites;
- logging e auditoria integral;
- dashboard local de observação e controlo;
- interface de interação orientada ao domínio do sistema;
- gestão de falhas, continuidade e recuperação;
- aprendizagem e ajuste supervisionado de parâmetros.

### Excluído do âmbito inicial
- trading de alta frequência;
- gestão multiutilizador empresarial;
- múltiplos brokers reais em simultâneo na primeira fase;
- autonomia irrestrita sem travões funcionais;
- alteração automática de lógica crítica sem rasto, validação e reversão.

## Objetivos funcionais de topo
1. Segurança funcional.
2. Rastreabilidade integral.
3. Supervisão humana efetiva.
4. Modularidade real.
5. Continuidade operacional controlada.
6. Aprendizagem supervisionada.

## Princípios obrigatórios
- fail-safe;
- validação antes de ação;
- separação de responsabilidades;
- racional explicável;
- persistência de contexto crítico;
- intervenção humana prioritária;
- evolução controlada.

## Estrutura modular principal
- FSD-100 — CORE
- FSD-200 — MARKET
- FSD-300 — DECISION
- FSD-400 — RISK
- FSD-500 — EXEC
- FSD-600 — DASH
- FSD-700 — RECOVERY
- FSD-800 — LEARN
- FSD-900 — USE CASES

## Estados globais
- Desligado
- Arranque
- Idle
- Monitorização
- Pronto para operar
- Operação ativa
- Bloqueado por risco
- Bloqueado por falha
- Erro
- Recuperação
- Treino/aprendizagem
- Manutenção

## Modos operacionais
- Observação
- Simulação/Demo
- Real
- Treino
- Manutenção

## Regras transversais
1. O sistema não pode operar sem dados válidos.
2. O sistema não pode operar com estado inconsistente.
3. O sistema não pode ignorar falhas críticas.
4. O sistema deve justificar decisões e bloqueios relevantes.
5. O sistema deve manter histórico suficiente para auditoria.
6. O sistema deve permitir bloqueio manual autorizado.
7. O sistema deve distinguir claramente os modos.
8. O sistema não deve aprender de forma destrutiva sem backup e reversão.
9. O sistema não deve assumir execução real sem confirmação externa válida.
10. O sistema deve sinalizar perda de integridade, latência excessiva ou ausência de sincronização.

---

# FSD-100 — CORE

## Missão
O CORE é o núcleo de governação funcional do sistema. Mantém o estado global, coordena arranque e paragem, controla modos operacionais, valida permissões antes de ações críticas e consolida alarmes e bloqueios sistémicos.

## Responsabilidades
1. Manter o estado global oficial do Odin.
2. Controlar transições válidas entre estados.
3. Impedir transições inválidas ou perigosas.
4. Validar pré-condições de arranque e ativação operacional.
5. Definir o modo operacional ativo.
6. Aplicar permissões e restrições por modo e estado.
7. Receber e consolidar alarmes críticos.
8. Forçar transição para estado seguro quando necessário.
9. Coordenar paragem controlada e retoma validada.
10. Fornecer uma fonte de verdade única para o estado do sistema.

## Estados globais
| Código | Estado |
|---|---|
| ST-00 | Desligado |
| ST-10 | Arranque |
| ST-20 | Idle |
| ST-30 | Monitorização |
| ST-40 | Pronto para operar |
| ST-50 | Operação ativa |
| ST-60 | Pausado |
| ST-70 | Bloqueado por risco |
| ST-80 | Bloqueado por falha |
| ST-90 | Erro |
| ST-100 | Recuperação |
| ST-110 | Treino/Aprendizagem |
| ST-120 | Manutenção |

## Modos operacionais
| Código | Modo |
|---|---|
| MD-10 | Observação |
| MD-20 | Demo |
| MD-30 | Real |
| MD-40 | Treino |
| MD-50 | Manutenção |

## Eventos principais
- EV-START
- EV-STOP
- EV-PAUSE
- EV-RESUME
- EV-MODE-CHANGE
- EV-RISK-BLOCK
- EV-FAULT-BLOCK
- EV-ERROR
- EV-RECOVERY
- EV-RECOVERY-OK
- EV-RECOVERY-FAIL
- EV-MARKET-READY
- EV-MARKET-INVALID

## Regras críticas
- Não é permitido Desligado → Operação ativa.
- Não é permitido Arranque → Operação ativa sem validação intermédia.
- Não é permitido Bloqueado por falha → Operação ativa sem recuperação.
- Não é permitido Erro → Operação ativa direta.
- Mudança para modo Real exige pré-condições reforçadas.

## Pré-condições de arranque
- configuração principal carregada;
- integridade mínima da configuração;
- logging funcional;
- módulos críticos disponíveis;
- consistência mínima do estado persistido;
- ausência de bloqueio administrativo;
- identificação do modo pretendido.

## Bloqueios sistémicos
- BLK-10 Bloqueio manual
- BLK-20 Bloqueio por risco
- BLK-30 Bloqueio por falha técnica
- BLK-40 Bloqueio administrativo
- BLK-50 Bloqueio por recuperação pendente

## Publicação do estado global
O CORE publica estado atual, modo atual, timestamp da última transição, origem da última transição, bloqueios ativos, indicadores resumidos de prontidão/integridade e motivo principal de limitação.

---

# FSD-200 — MARKET

## Missão
O módulo MARKET disponibiliza ao Odin uma visão funcionalmente válida do mercado e do contexto operacional: recolha de dados, validação temporal/lógica, deteção de disponibilidade do mercado, classificação de contexto e sinalização de degradação.

## Responsabilidades
1. Recolher dados mínimos dos instrumentos configurados.
2. Validar integridade temporal e estrutural.
3. Determinar se o mercado está funcionalmente aberto.
4. Identificar sessão de mercado relevante.
5. Integrar eventos macroeconómicos, quando disponíveis.
6. Classificar o contexto operacional do mercado.
7. Sinalizar perda de feed, atraso ou anomalia.
8. Informar o CORE sobre prontidão, invalidez ou degradação.
9. Fornecer ao RISK e DECISION contexto resumido.
10. Registar eventos críticos de mercado e integridade.

## Categorias de dados
| Código | Categoria |
|---|---|
| MK-10 | Dados de preço |
| MK-20 | Estado de mercado |
| MK-30 | Sessão de mercado |
| MK-40 | Eventos externos |
| MK-50 | Integridade do feed |
| MK-60 | Contexto resumido |

## Estados funcionais
| Código | Estado |
|---|---|
| MS-10 | Válido |
| MS-20 | Degradado |
| MS-30 | Inválido |
| MS-40 | Fechado |
| MS-50 | Indisponível |

## Contexto resumido
| Código | Contexto |
|---|---|
| MC-10 | Favorável |
| MC-20 | Neutro |
| MC-30 | Sensível |
| MC-40 | Hostil |
| MC-50 | Indeterminado |

## Dados mínimos obrigatórios
- instrumento observado;
- preço ou conjunto mínimo de preços;
- timestamp da última atualização válida;
- estado de validade do dado;
- estado do mercado;
- sessão ou janela temporal relevante;
- contexto resumido.

## Regras críticas
- dado ausente não é dado válido;
- dado demasiado antigo deve ser inválido ou degradado;
- mercado fechado impede prontidão para operação real;
- contexto indeterminado não deve ser tratado como neutro;
- perda total de feed resulta em estado Indisponível.

## Saídas de prontidão
- pronto;
- pronto com restrições;
- não pronto;
- indisponível.

---

# FSD-300 — DECISION

## Missão
O módulo DECISION converte dados válidos, contexto operacional e permissões funcionais numa decisão operacional clara, auditável e disciplinada.

## Responsabilidades
1. Receber dados/contexto válidos do MARKET.
2. Receber permissões/restrições de CORE e RISK.
3. Avaliar táticas ativas.
4. Calcular score individual por hipótese.
5. Aplicar filtros mínimos de elegibilidade.
6. Ordenar hipóteses elegíveis.
7. Determinar o resultado do ciclo decisório.
8. Emitir racional estruturado.
9. Gerar intenção operacional única, quando aplicável.
10. Registar a decisão e alternativas rejeitadas relevantes.

## Estrutura de táticas
Cada tática ativa deve ter:
- identificador único;
- estado ativa/inativa;
- critérios mínimos de elegibilidade;
- fatores de scoring;
- peso/prioridade base;
- limiar mínimo;
- regras de exclusão.

## Estados internos
| Código | Estado |
|---|---|
| DS-10 | Aguardando inputs |
| DS-20 | Pronto a avaliar |
| DS-30 | Em avaliação |
| DS-40 | Sem oportunidade válida |
| DS-50 | Oportunidade selecionada |
| DS-60 | Bloqueado externamente |
| DS-70 | Intenção emitida |
| DS-80 | Erro decisório |

## Saídas do ciclo
| Código | Saída |
|---|---|
| DV-10 | Não operar |
| DV-20 | Aguardar |
| DV-30 | Operar candidato |
| DV-40 | Restringir |
| DV-50 | Bloquear |
| DV-60 | Encerrar decisão com erro |

## Regras críticas
- não operar também é decisão legítima;
- score sem explicação funcional não é aceitável;
- ausência de confluência mínima pode invalidar hipótese;
- o sistema deve distinguir hipótese inexistente, fraca e válida mas bloqueada externamente;
- a saída do ciclo deve ser única, clara e rastreável.

## Intenção operacional
Quando existir, deve conter:
- identificador da tática selecionada;
- identificador do ciclo decisório;
- timestamp da decisão;
- direção/tipo de intenção;
- score final;
- resumo do racional;
- restrições relevantes;
- validade temporal.

---

# FSD-400 — RISK

## Missão
O módulo RISK impõe disciplina de exposição, limita comportamento operacional, aplica travões de segurança e bloqueia o sistema quando as condições deixam de ser aceitáveis.

## Responsabilidades
1. Definir e aplicar limites por operação.
2. Definir e aplicar limites agregados por período.
3. Controlar exposição simultânea.
4. Restringir frequência operacional.
5. Monitorizar sequências de perda.
6. Identificar degradação persistente.
7. Produzir estado permitido/restrito/bloqueado.
8. Emitir bloqueios por risco ao CORE.
9. Manter histórico mínimo de risco.
10. Permitir reentrada apenas com critério de desbloqueio válido.

## Saídas de risco
| Código | Saída |
|---|---|
| RK-ALLOW | Permitido |
| RK-RESTRICT | Restrito |
| RK-BLOCK | Bloqueado |
| RK-KILL | Kill-switch |

## Categorias de risco
- RC-10 Risco por operação
- RC-20 Risco agregado diário
- RC-30 Risco agregado semanal
- RC-40 Risco por exposição simultânea
- RC-50 Risco por sequência negativa
- RC-60 Risco por frequência excessiva
- RC-70 Risco contextual
- RC-80 Risco sistémico

## Estados internos
| Código | Estado |
|---|---|
| RS-10 | Normal |
| RS-20 | Restrito |
| RS-30 | Bloqueado |
| RS-40 | Kill ativo |
| RS-50 | Degradado |

## Regras críticas
- capital preservado antes de performance;
- oportunidade não justifica violar limites;
- contexto hostil reduz permissões;
- o sistema não pode aumentar risco para recuperar perdas;
- kill-switch não deve ser limpo automaticamente.

## Limites mínimos suportados
- risco máximo por operação;
- tamanho máximo de posição;
- perda máxima diária;
- perda máxima semanal;
- número máximo de operações por período;
- número máximo de perdas consecutivas;
- exposição simultânea máxima;
- cooldown após perda.

---

# FSD-500 — EXEC

## Missão
O módulo EXEC transforma uma intenção operacional formal do DECISION numa ação externa controlada, desde que todas as permissões e validações finais se mantenham válidas.

## Responsabilidades
1. Receber intenções operacionais formais.
2. Validar validade temporal e consistência da intenção.
3. Confirmar permissões de CORE, MARKET e RISK.
4. Preparar submissão operacional.
5. Submeter a ação/ordem.
6. Capturar resultado inicial.
7. Confirmar estado real da execução.
8. Reconciliar estado interno com evidência externa.
9. Emitir eventos de sucesso, rejeição, falha, pendência ou divergência.
10. Bloquear continuação cega quando a reconciliação não for confiável.

## Estados internos
| Código | Estado |
|---|---|
| ES-10 | À espera de intenção |
| ES-20 | Intenção recebida |
| ES-30 | Validação pré-execução |
| ES-40 | Pronto a submeter |
| ES-50 | Submetido |
| ES-60 | Pendente de confirmação |
| ES-70 | Confirmado executado |
| ES-80 | Rejeitado |
| ES-90 | Falhado |
| ES-100 | Divergente |
| ES-110 | Cancelado/expirado |

## Resultado inicial
| Código | Resultado |
|---|---|
| ER-10 | Aceite |
| ER-20 | Rejeitado |
| ER-30 | Pendente |
| ER-40 | Falha técnica |
| ER-50 | Ambíguo |

## Resultado consolidado
| Código | Resultado |
|---|---|
| EX-10 | Executado confirmado |
| EX-20 | Rejeitado confirmado |
| EX-30 | Falha confirmada |
| EX-40 | Pendente de resolução |
| EX-50 | Divergência crítica |
| EX-60 | Cancelado/expirado |

## Regras críticas
- intenção operacional deve ser revalidada antes da execução;
- o sistema não assume sucesso só porque tentou submeter;
- divergência é evento crítico;
- prevenir duplicação por idempotência;
- é preferível bloquear do que seguir sem saber o estado real.

---

# FSD-600 — DASH

## Missão
O módulo DASH disponibiliza ao utilizador uma interface operacional clara, disciplinada e orientada à supervisão do Odin.

## Responsabilidades
1. Expor o estado global oficial do sistema.
2. Expor o estado resumido dos módulos críticos.
3. Apresentar contexto atual do mercado.
4. Apresentar decisão atual/recente e racional.
5. Apresentar envelope de risco e bloqueios.
6. Apresentar estado de execução e divergências.
7. Apresentar recuperação/incidentes.
8. Permitir ações manuais autorizadas.
9. Disponibilizar consulta e exportação de logs/histórico.
10. Disponibilizar interação assistida no domínio autorizado.

## Áreas funcionais
1. Área de estado global
2. Área de observação operacional
3. Área de controlo manual
4. Área de alarmes e eventos críticos
5. Área de histórico e logs
6. Área de interação assistida

## Painéis mínimos
- Mercado e contexto
- Decisão e táticas
- Risco e travões
- Execução
- Recuperação/incidentes

## Ações mínimas
- Start
- Stop
- Pause
- Resume
- Bloqueio manual
- Entrada em manutenção
- Pedido de recuperação/validação
- Exportação de logs

## Regras críticas
- fonte de verdade única: CORE;
- clareza antes de estética;
- separar observar de atuar;
- estado crítico tem de ser inequívoco;
- interação assistida limitada ao domínio autorizado.

## Perguntas pré-definidas mínimas
- Qual é o estado atual do Odin?
- Porque está bloqueado?
- Qual foi a última decisão?
- Porque não entrou em operação?
- Qual é o estado do risco?
- Existe alguma divergência de execução?
- O mercado está utilizável neste momento?
- Há incidentes ou recuperação pendente?
- O que aconteceu nos últimos X minutos?

---

# FSD-700 — RECOVERY

## Missão
O módulo RECOVERY garante que o Odin consegue responder a incidentes operacionais sem perder controlo funcional, sem assumir estados falsos e sem regressar cegamente à atividade.

## Responsabilidades
1. Identificar incidentes que exigem recuperação funcional.
2. Coordenar transição para estado seguro com o CORE.
3. Ler e validar contexto persistido relevante.
4. Obter evidência externa suficiente para reconstrução de estado.
5. Determinar consistência ou divergência entre estados.
6. Produzir resultado de recuperação.
7. Coordenar retoma controlada.
8. Impedir regresso automático quando a recuperação é inconclusiva.
9. Registar trilho completo do incidente e da recuperação.
10. Informar DASH, CORE, EXEC e RISK do estado de recuperação.

## Eventos que acionam recuperação
- RVY-10 Reinício inesperado
- RVY-20 Falha de energia
- RVY-30 Perda de internet/comunicação crítica
- RVY-40 Perda prolongada de feed
- RVY-50 Divergência de execução
- RVY-60 Corrupção/incoerência de estado persistido
- RVY-70 Falha crítica de módulo
- RVY-80 Comando manual de recuperação

## Estados internos
| Código | Estado |
|---|---|
| RSY-10 | Inativo |
| RSY-20 | Incidente detetado |
| RSY-30 | Preservação/Leitura de contexto |
| RSY-40 | Reconciliação em curso |
| RSY-50 | Recuperado com sucesso |
| RSY-60 | Recuperado com restrições |
| RSY-70 | Bloqueado por incerteza |
| RSY-80 | Falha de recuperação |
| RSY-90 | A aguardar intervenção |

## Resultados de recuperação
| Código | Resultado |
|---|---|
| RCV-10 | Recuperação validada |
| RCV-20 | Recuperação validada com restrições |
| RCV-30 | Recuperação inconclusiva |
| RCV-40 | Recuperação falhada |
| RCV-50 | Intervenção necessária |

## Regras críticas
- recuperar não é continuar;
- estado observado prevalece sobre memória incerta;
- incerteza favorece bloqueio;
- não regressar diretamente a operação ativa sem revalidação completa;
- determinados casos exigem intervenção humana explícita.

---

# FSD-800 — LEARN

## Missão
O módulo LEARN permite evolução controlada do comportamento do Odin com base em histórico operacional, desempenho observado e regras de governação definidas.

## Responsabilidades
1. Recolher histórico operacional relevante.
2. Estruturar dados de desempenho por tática, período e contexto.
3. Avaliar comportamento recente e histórico consolidado.
4. Identificar candidatos a ajuste dentro das fronteiras permitidas.
5. Propor ou aplicar ajustes de parâmetros/pesos autorizados.
6. Criar backup/versionamento antes de alterações.
7. Registar racional, origem e impacto esperado.
8. Marcar versões como ativas, em teste, aprovadas ou revertidas.
9. Permitir reversão controlada.
10. Informar CORE, DASH e componentes dependentes.

## Tipos de alteração permitidos
| Código | Tipo |
|---|---|
| LG-10 | Ajuste de pesos |
| LG-20 | Ajuste de limiares |
| LG-30 | Ajuste de prioridade |
| LG-40 | Desativação preventiva |
| LG-50 | Reativação controlada |

## Estados internos
| Código | Estado |
|---|---|
| LS-10 | Inativo |
| LS-20 | A recolher histórico |
| LS-30 | Em análise |
| LS-40 | Proposta gerada |
| LS-50 | Aguardando aprovação |
| LS-60 | A preparar ativação |
| LS-70 | Versão ativa em observação |
| LS-80 | Revertido |
| LS-90 | Bloqueado |
| LS-100 | Erro de aprendizagem |

## Modos de aprovação
| Código | Modo |
|---|---|
| AP-10 | Aprovação manual |
| AP-20 | Aprovação automática limitada |
| AP-30 | Aprovação para teste |

## Regras críticas
- aprender não é improvisar;
- produção e treino não se confundem;
- nenhuma mudança relevante sem rollback possível;
- privilegiar qualidade do histórico e explicabilidade;
- na dúvida, manter configuração segura.

## Conteúdo mínimo da proposta
- identificador único;
- versão base;
- parâmetros/pesos a alterar;
- valores anteriores e novos;
- motivo principal;
- evidência resumida;
- tipo de ativação;
- critério de rollback, quando aplicável.

---

# FSD-900 — USE CASES

## Objetivo
Ligar estados, contexto de mercado, decisão, risco, execução, recuperação, dashboard e aprendizagem em cenários ponta-a-ponta.

## Casos de uso fundamentais
1. Arranque normal do sistema
2. Sistema em observação com mercado fechado
3. Mercado válido, sem oportunidade operacional
4. Oportunidade válida em modo Demo
5. Oportunidade válida em modo Real com execução confirmada
6. Oportunidade válida bloqueada por RISK
7. Oportunidade válida invalidada antes da execução
8. Divergência de execução
9. Perda de feed durante operação/monitorização
10. Reinício inesperado com recuperação segura
11. Pausa manual e retoma controlada
12. Kill-switch manual ou automático
13. Entrada em manutenção
14. Geração de proposta de aprendizagem
15. Ativação de nova versão com snapshot
16. Reversão / rollback após degradação
17. Consulta operacional via dashboard
18. Exportação de logs após incidente

## Regras transversais
- nenhum caso de uso contorna a autoridade do CORE sobre estado global;
- nenhum caso de uso contorna a autoridade do RISK sobre bloqueios;
- nenhum caso de uso ignora a validade declarada pelo MARKET;
- nenhum caso de uso trata intenção como execução confirmada sem passar pelo EXEC;
- nenhum caso de uso de falha/recuperação regressa diretamente a operação ativa sem revalidação;
- nenhum caso de uso de aprendizagem altera produção sem snapshot e versionamento.

## Matriz resumida de cobertura
| Caso de uso | CORE | MARKET | DECISION | RISK | EXEC | RECOVERY | DASH | LEARN |
|---|---|---|---|---|---|---|---|---|
| UC-001 Arranque normal | X | X |  |  |  | X | X |  |
| UC-002 Mercado fechado | X | X | X | X |  |  | X |  |
| UC-003 Sem oportunidade | X | X | X | X |  |  | X |  |
| UC-004 Operação Demo | X | X | X | X | X |  | X |  |
| UC-005 Operação Real confirmada | X | X | X | X | X |  | X |  |
| UC-006 Bloqueio por risco | X |  | X | X |  |  | X |  |
| UC-007 Intenção invalidada | X | X | X | X | X |  | X |  |
| UC-008 Divergência | X |  |  | X | X | X | X |  |
| UC-009 Perda de feed | X | X | X | X |  | X | X |  |
| UC-010 Reinício/recuperação | X | X |  | X | X | X | X |  |
| UC-011 Pausa/retoma | X | X | X | X |  |  | X |  |
| UC-012 Kill-switch | X |  |  | X | X |  | X |  |
| UC-013 Manutenção | X |  |  | X | X |  | X |  |
| UC-014 Proposta de aprendizagem |  |  | X |  |  |  | X | X |
| UC-015 Ativação nova versão | X |  | X | X |  |  | X | X |
| UC-016 Rollback | X |  | X |  |  |  | X | X |
| UC-017 Consulta operacional | X | X | X | X | X | X | X |  |
| UC-018 Exportação de logs |  |  |  |  |  |  | X |  |

---

# ODIN — MATRIZ MESTRA

## Finalidade
Consolidar a estrutura documental, funcional e de governação do projeto Odin, servindo como ponte entre os FSD, a futura arquitetura técnica (SDS), os testes e a implementação faseada.

## Árvore documental principal
| Código | Documento | Estado | Finalidade |
|---|---|---|---|
| FSD-000 | MASTER | Criado | Visão funcional global |
| FSD-100 | CORE | Criado | Estados globais, modos e permissões |
| FSD-200 | MARKET | Criado | Dados de mercado e contexto |
| FSD-300 | DECISION | Criado | Táticas, scoring e racional |
| FSD-400 | RISK | Criado | Limites e travões |
| FSD-500 | EXEC | Criado | Execução e reconciliação |
| FSD-600 | DASH | Criado | Dashboard e controlo humano |
| FSD-700 | RECOVERY | Criado | Recuperação e reconstrução de estado |
| FSD-800 | LEARN | Criado | Aprendizagem, snapshots e rollback |
| FSD-900 | USE CASES | Criado | Integração funcional ponta-a-ponta |

## Mapa dos módulos funcionais
| Módulo | Documento principal | Missão funcional |
|---|---|---|
| CORE | FSD-100 | Governação do estado global |
| MARKET | FSD-200 | Verdade operacional do mercado |
| DECISION | FSD-300 | Converter contexto em decisão auditável |
| RISK | FSD-400 | Impor limites e travões |
| EXEC | FSD-500 | Executar intenções válidas com confirmação |
| DASH | FSD-600 | Tornar o sistema observável e controlável |
| RECOVERY | FSD-700 | Restaurar controlo após incidentes |
| LEARN | FSD-800 | Evoluir o sistema sem o desalinhar |

## Estados globais mestres
- ST-00 Desligado
- ST-10 Arranque
- ST-20 Idle
- ST-30 Monitorização
- ST-40 Pronto para operar
- ST-50 Operação ativa
- ST-60 Pausado
- ST-70 Bloqueado por risco
- ST-80 Bloqueado por falha
- ST-90 Erro
- ST-100 Recuperação
- ST-110 Treino/Aprendizagem
- ST-120 Manutenção

## Modos operacionais mestres
- MD-10 Observação
- MD-20 Demo
- MD-30 Real
- MD-40 Treino
- MD-50 Manutenção

## Eventos mestres do sistema
- EV-START
- EV-STOP
- EV-PAUSE
- EV-RESUME
- EV-MODE-CHANGE
- EV-MARKET-READY
- EV-MARKET-INVALID
- EV-RISK-BLOCK
- EV-FAULT-BLOCK
- EV-ERROR
- EV-RECOVERY
- EV-RECOVERY-OK
- EV-RECOVERY-FAIL
- RV-KILL
- EX-DIVERGENCE
- LEARN-PROPOSE
- LEARN-ACTIVATE
- LEARN-ROLLBACK

## Matriz de dependências entre módulos
| Módulo | Depende de |
|---|---|
| CORE | — |
| MARKET | CORE |
| DECISION | CORE, MARKET, RISK |
| RISK | CORE, MARKET, histórico operacional |
| EXEC | CORE, MARKET, RISK, DECISION |
| DASH | CORE, MARKET, DECISION, RISK, EXEC, RECOVERY, LEARN |
| RECOVERY | CORE, EXEC, MARKET, RISK, persistência |
| LEARN | CORE, DECISION, histórico, RISK |

## Matriz de autoridade funcional
| Assunto | Autoridade principal |
|---|---|
| Estado global | CORE |
| Validade do mercado | MARKET |
| Escolha da hipótese operacional | DECISION |
| Permissão de risco | RISK |
| Estado da execução | EXEC |
| Recuperação após falha | RECOVERY |
| Observabilidade e controlo humano | DASH |
| Evolução de pesos e versões | LEARN |

## Prioridade de implementação
| Prioridade | Módulo |
|---|---|
| P1 | CORE |
| P1 | RISK |
| P1 | MARKET |
| P1 | DECISION |
| P1 | EXEC |
| P1 | RECOVERY |
| P2 | DASH |
| P2 | LEARN |
| P2 | USE CASES |

## Fases do projeto
| Fase | Objetivo | Módulos mínimos |
|---|---|---|
| Fase 1 | Fundação operacional | CORE, DASH mínimo, logging base |
| Fase 2 | Consciência de mercado | MARKET, CORE |
| Fase 3 | Decisão disciplinada | DECISION, RISK, MARKET, CORE |
| Fase 4 | Execução controlada | EXEC, DECISION, RISK, CORE, MARKET |
| Fase 5 | Resiliência | RECOVERY, EXEC, CORE |
| Fase 6 | Supervisão madura | DASH completo |
| Fase 7 | Evolução controlada | LEARN |

## Rastreabilidade macro
| Requisito macro | Documento principal |
|---|---|
| Estado global coerente | FSD-100 |
| Mercado válido vs inválido | FSD-200 |
| Decisão auditável | FSD-300 |
| Bloqueio por risco | FSD-400 |
| Execução e reconciliação corretas | FSD-500 |
| Recuperação após incidente | FSD-700 |
| Observação e controlo humano | FSD-600 |
| Evolução com rollback | FSD-800 |

## Artefactos futuros
- SDS — Software Design Specification
- TAD — Technical Architecture Document
- Test Plan
- Matriz de rastreabilidade detalhada
- Runbook operacional
- Plano de observabilidade
- Plano de versionamento

## Ordem recomendada para SDS
1. SDS-CORE / STATE-MACHINE / LOGGING / CONFIG
2. SDS-MARKET / DECISION / RISK / EXEC
3. SDS-RECOVERY / DASH / ALERTING
4. SDS-LEARN / VERSIONING / ROLLBACK

## Mínimo operacional viável do Odin
- CORE com estados e transições base
- MARKET com validade mínima do feed e mercado aberto/fechado
- DECISION com uma tática simples e racional básico
- RISK com bloqueio por operação e perda diária
- EXEC em demo com confirmação básica
- DASH mínimo com estado global, decisão, risco e logs
- RECOVERY mínimo para reinício inesperado

## Próximos passos obrigatórios
1. Revisão cruzada dos FSD para normalizar terminologia, códigos e estados.
2. Criação da matriz de rastreabilidade detalhada.
3. Início do SDS pelo pacote CORE.

---

# REFORÇOS FINAIS DE POLIMENTO — v0.4

## 1. Evento obrigatório de expiração de intenção (DECISION / EXEC)

Para eliminar expiração silenciosa entre os módulos **DECISION** e **EXEC**, fica definido o seguinte evento funcional adicional:

- **EV-INTENTION-EXPIRED** — evento emitido pelo EXEC quando uma intenção operacional recebida já se encontra expirada no momento da validação pré-execução.

### Regra obrigatória
Se o EXEC receber uma intenção em que:
- `now > expires_at`; ou
- `ttl_ms` tenha sido ultrapassado; ou
- a intenção deixe de ser válida por atraso incompatível com a janela operacional;

então o EXEC deverá obrigatoriamente:
1. rejeitar a intenção sem submissão externa;
2. emitir `EV-INTENTION-EXPIRED`;
3. registar log crítico com `intent_id`, `decision_cycle_id`, `created_at`, `expires_at`, `now` e diferença temporal;
4. publicar o evento ao CORE e ao DASH;
5. classificar o ciclo executório como **cancelado/expirado**.

### Impacto funcional
- O operador passa a saber que a oportunidade foi perdida por latência.
- O sistema ganha observabilidade para afinação posterior do pipeline.
- A expiração deixa de ser uma falha silenciosa.

### Impacto nos módulos
- **FSD-300 — DECISION:** a intenção operacional deve conter obrigatoriamente `intent_id`, `decision_cycle_id`, `created_at`, `ttl_ms` e `expires_at`.
- **FSD-500 — EXEC:** a validação pré-execução deve incluir emissão explícita de `EV-INTENTION-EXPIRED`.
- **FSD-600 — DASH:** o dashboard deve poder mostrar “intenção expirada antes da execução” como motivo distinto de rejeição normal.

---

## 2. Hierarquia de bloqueios e precedência de desbloqueio (CORE / RISK / RECOVERY)

Para remover ambiguidades entre bloqueios manuais, bloqueios automáticos e resultados de recuperação, fica definida a seguinte regra transversal de precedência.

### Hierarquia funcional de bloqueios
Da maior para a menor precedência operacional:
1. **Kill-switch ativo**
2. **Bloqueio manual explícito**
3. **Bloqueio por falha / integridade / recovery pendente**
4. **Bloqueio por risco**
5. **Restrição operacional**
6. **Estado operacional normal autorizado**

### Regra crítica de desbloqueio
Um bloqueio de precedência superior **não pode** ser limpo implicitamente por evento de precedência inferior.

### Regra específica obrigatória
Um **BLK-10 — Bloqueio manual**:
- não pode ser removido por `RCV-10 — Recuperação validada`;
- não pode ser removido por retorno do MARKET a estado válido;
- não pode ser removido por cooldown automático do RISK;
- não pode ser removido por simples transição automática do CORE.

A remoção de bloqueio manual exige sempre:
- ação manual autorizada; e
- evento explícito de desbloqueio/retoma, por exemplo `EV-RESUME` ou equivalente funcional aprovado.

### Regras adicionais
- Se coexistirem vários bloqueios, o sistema deverá publicar o bloqueio de maior precedência como **motivo dominante**, sem ocultar os restantes.
- A recuperação pode limpar bloqueios de recuperação/falha que lhe pertençam, mas não bloqueios manuais.
- O DASH deve distinguir entre bloqueio ainda ativo por decisão humana e bloqueio já tecnicamente resolvido mas mantido por ação manual anterior.

---

## 3. Filtro preventivo de notícias e “pânico” contextual (MARKET)

Os critérios quantitativos de spread, latência e volatilidade são necessários, mas não suficientes. Há janelas em que o preço ainda parece “normal” imediatamente antes de eventos macroeconómicos de alto impacto. Para impedir falsa normalidade, fica definido o seguinte reforço funcional.

### Regra de filtro preventivo de notícias
Se existir evento macroeconómico classificado como **alto impacto** dentro da janela de guarda configurada, o módulo **MARKET** deverá forçar o contexto resumido para estado preventivo agravado, independentemente de o preço atual ainda parecer estável.

### Política mínima recomendada
- Evento de alto impacto dentro de **5 minutos** da janela operacional:
  - contexto mínimo: **MC-30 — Sensível**
- Evento de alto impacto dentro da janela crítica definida pela política mais restritiva:
  - contexto pode ser forçado para **MC-40 — Hostil**
- A mesma lógica poderá aplicar-se a uma janela pós-evento, conforme configuração.

### Regras obrigatórias
- O contexto preventivo por notícia não depende apenas de spread atual ou ATR instantâneo.
- A ausência de expansão de spread no minuto presente não invalida a classificação preventiva.
- Se a fonte de notícias/eventos estiver indisponível e o modo operativo depender dela, o MARKET deve sinalizar **informação crítica indisponível**, e não normalidade total.
- O RISK e o DECISION devem consumir esta classificação preventiva como entrada legítima para restrição ou bloqueio.

---

## 4. Estado documental após v0.4

Com estes reforços, o documento consolidado passa a incluir adicionalmente:
- observabilidade explícita de expiração de intenção;
- precedência formal entre bloqueios e desbloqueios;
- filtro preventivo de notícias/eventos macro de alto impacto.

Estes pontos fecham lacunas relevantes para transição do FSD para o SDS, especialmente nas áreas de:
- concorrência temporal;
- governação de bloqueios;
- robustez contextual do mercado.

---

## 5. Próxima etapa recomendada

Após esta v0.4, o documento FSD pode ser tratado como **baseline funcional congelada**, e o passo tecnicamente correto passa a ser:
1. **ODIN-CORE-STATE-AND-EVENT-MODEL.md**
2. **SDS-100 — CORE**
3. **ODIN-TRACEABILITY-MATRIX.md**

---

# REFORÇOS DE ENGENHARIA FUNCIONAL — v0.4

## 1. Monitor de Heartbeat e cegueira modular (CORE)

Para reduzir o risco de **cegueira modular** — situação em que um módulo deixa de responder sem emitir erro formal — fica introduzido o mecanismo funcional de heartbeat supervisionado pelo **CORE**.

### Regra funcional obrigatória
Todos os módulos críticos ativos devem publicar heartbeat periódico ao CORE.

### Módulos críticos mínimos
- **MARKET**
- **RISK**
- **EXEC**

### Módulos recomendados
- **DECISION**
- **RECOVERY**

### Campos mínimos do heartbeat
Cada heartbeat deverá conter, no mínimo:
- `module_id`
- `timestamp`
- `module_state`
- `mode_context`
- `sequence_number`
- indicador mínimo de saúde funcional

### Regra crítica
Se o CORE detetar ausência de heartbeat de um módulo crítico por mais de `heartbeat_timeout_cycles` ou `heartbeat_timeout_ms`, deverá:
1. marcar o módulo como não confiável;
2. adicionar bloqueio de falha ao vetor de bloqueios ativos;
3. forçar transição para **ST-80 — Bloqueado por falha**, salvo se já existir estado de precedência superior;
4. publicar evento crítico ao DASH e aos módulos dependentes.

### Efeito funcional
- deteção de zombie processes e deadlocks funcionais;
- redução do risco de continuar a operar com módulo “morto mas sem erro declarado”;
- maior determinismo no CORE.

### Impacto nos módulos
- **FSD-100 — CORE:** passa a incluir supervisão de liveness por heartbeat.
- **FSD-600 — DASH:** deve conseguir mostrar “módulo sem heartbeat” como causa de bloqueio.
- **FSD-700 — RECOVERY:** perda prolongada de heartbeat pode ser gatilho de recuperação ou bloqueio.

---

## 2. Spread adaptativo e liquidez implícita (MARKET)

Para reforçar a robustez do **MARKET**, fica definido que preço “vivo” não basta para classificar o mercado como utilizável.

### Métrica funcional adicional obrigatória
O MARKET deve avaliar também:
- `spread_current`
- `spread_avg_ref`
- `spread_ratio = spread_current / spread_avg_ref`

onde `spread_avg_ref` deverá ser parametrizável, por exemplo:
- média móvel de 24h;
- média por sessão;
- média ponderada por janela equivalente.

### Regras funcionais recomendadas
O sistema deverá suportar, no mínimo:
- **MS-20 — Degradado** quando `spread_ratio > spread_multiplier_degraded`
- **MC-40 — Hostil** quando:
  - `spread_ratio > spread_multiplier_hostile`; ou
  - `spread_current > spread_absolute_critical`

### Regras obrigatórias
- Feed vivo com spread anormal não deve ser tratado como condição operacional normal.
- Mercados de liquidez fraca, como certas aberturas ou transições de sessão, devem poder ser degradados preventivamente.
- Spread excessivo deve influenciar tanto o estado do MARKET como o contexto resumido consumido por DECISION e RISK.

### Impacto nos módulos
- **FSD-200 — MARKET:** passa a incluir spread adaptativo como métrica nativa de qualidade.
- **FSD-300 — DECISION:** poderá descartar hipóteses válidas em contexto de spread hostil.
- **FSD-400 — RISK:** poderá restringir ou bloquear operação por custo implícito excessivo.
- **FSD-600 — DASH:** deve mostrar spread anormal como motivo explícito de degradação.

---

## 3. Kill-switch persistente e sobrevivência a reboot (RISK / CORE)

O estado de **Kill-switch ativo** passa a ter obrigatoriamente persistência fora de memória volátil.

### Regra de ouro
Se existir `kill_flag` persistida, o arranque do sistema em **ST-10 — Arranque** deve obrigatoriamente validá-la antes de permitir qualquer progressão operacional.

### Regras obrigatórias
Se o `kill_flag` persistido existir:
1. o CORE não pode permitir transição para:
   - `ST-20 — Idle`
   - `ST-30 — Monitorização`
   - `ST-40 — Pronto para operar`
   - `ST-50 — Operação ativa`
2. o sistema deverá entrar em estado bloqueado compatível ou modo de manutenção;
3. a limpeza do kill persistente exige ação autorizada e auditável;
4. reboot do SO ou restart do processo não pode limpar o kill-switch.

### Efeito funcional
- impede que um crash seguido de reboot limpe proteção crítica;
- torna o kill-switch uma trava séria e não apenas um estado volátil.

### Impacto nos módulos
- **FSD-400 — RISK:** `RS-40 — Kill ativo` deve persistir.
- **FSD-100 — CORE:** arranque deve validar kill persistido.
- **FSD-700 — RECOVERY:** recuperação não limpa kill persistente automaticamente.
- **FSD-600 — DASH:** deve mostrar kill persistido como causa dominante de bloqueio.

---

## 4. Controlo de slippage e rejeição por desvio (EXEC)

A intenção operacional passa a incluir tolerância máxima de slippage.

### Novo campo obrigatório na intenção operacional
- `max_slippage`

### Novo evento funcional
- **EV-EXEC-REJECTED-SLIPPAGE**

### Regras funcionais
O módulo EXEC deverá distinguir pelo menos dois cenários:

#### 4.1 Rejeição preventiva
Se, antes da submissão efetiva, a estimativa de execução já exceder `max_slippage`, o EXEC deverá:
1. rejeitar a intenção;
2. não submeter a ordem;
3. emitir `EV-EXEC-REJECTED-SLIPPAGE`;
4. registar o motivo em log crítico.

#### 4.2 Divergência pós-submissão
Se a submissão ocorrer mas a confirmação externa indicar preço fora do `max_slippage`, o EXEC deverá:
1. classificar a situação como divergência ou execução fora da tolerância;
2. emitir evento de severidade crítica;
3. informar CORE, RISK e DASH;
4. permitir entrada em recuperação, se aplicável.

### Regras obrigatórias
- O EXEC não deve tratar slippage excessivo como execução normal.
- `max_slippage` deve ser interpretado como limite funcional de aceitabilidade, não como campo decorativo.

### Impacto nos módulos
- **FSD-300 — DECISION:** intenção operacional deve incluir `max_slippage`.
- **FSD-500 — EXEC:** passa a ter rejeição/alerta explícito por slippage.
- **FSD-600 — DASH:** deve distinguir rejeição normal de rejeição por slippage.

---

## 5. Vetor de bloqueios ativos e rastreabilidade de causa raiz (CORE / DASH)

Para evitar perda de rastreabilidade quando coexistem vários bloqueios, o CORE passa a manter um **vetor completo de bloqueios ativos**.

### Estrutura funcional mínima
O estado global consolidado deve conter:
- `dominant_block_reason`
- `active_block_vector[]`
- `block_origin`
- `block_timestamp`
- `block_clear_condition`

### Regras obrigatórias
- O bloqueio dominante é apenas a causa principal apresentada prioritariamente.
- Os restantes bloqueios ativos não podem ser descartados da memória funcional.
- O sistema só deve sair de estado bloqueado quando o vetor de bloqueios impeditivos estiver vazio ou reduzido a condições compatíveis com o estado de destino.
- Limpar um bloqueio não pode mascarar outro ainda ativo.

### Efeito funcional
- maior clareza de causa raiz;
- melhor diagnóstico de “porque não arranca”;
- melhor coordenação entre CORE, RISK, RECOVERY e DASH.

### Impacto nos módulos
- **FSD-100 — CORE:** passa a manter vetor de bloqueios e não apenas motivo dominante.
- **FSD-600 — DASH:** deve ser capaz de listar todos os bloqueios ativos.
- **FSD-700 — RECOVERY:** deve consultar o vetor completo antes de autorizar retoma.

---

## 6. Modo Manutenção com perfil de saída explícito (CORE / DASH / EXEC)

A entrada em **MD-50 / ST-120 — Manutenção** passa a exigir um perfil funcional de comportamento relativamente a posições, intenções e execução.

### Perfis mínimos suportados

#### `maintenance_soft`
- bloqueia novas intenções;
- bloqueia novas execuções;
- mantém posições já protegidas ou estado externo estável;
- não força encerramento agressivo.

#### `maintenance_managed_exit`
- bloqueia novas entradas;
- permite ou solicita fecho controlado das posições conforme política.

#### `maintenance_hard_exit`
- força encerramento máximo permitido pelo sistema/canal, sujeito a segurança operacional.

### Regra obrigatória
Ao ativar o modo de manutenção, o operador autorizado deve escolher explicitamente o perfil de saída.

### Fallback obrigatório
Na ausência de escolha explícita, o sistema deverá assumir por defeito:
- **`maintenance_soft`**

### Regras adicionais
- O perfil selecionado deve ficar registado em log auditável.
- O DASH deve mostrar claramente o perfil de manutenção ativo.
- O EXEC deve respeitar o perfil de manutenção como restrição dominante.

### Impacto nos módulos
- **FSD-100 — CORE:** manutenção deixa de ser um estado neutro; passa a ter perfil comportamental.
- **FSD-500 — EXEC:** deve adaptar permissões ao perfil de manutenção.
- **FSD-600 — DASH:** deve apresentar e pedir escolha do perfil de manutenção.

---

## 7. Estado documental após v0.4

Com estes reforços, o documento consolidado passa a incluir adicionalmente:
- supervisão de liveness por heartbeat;
- controlo contextual de spread e liquidez implícita;
- kill-switch persistente sobrevivente a reboot;
- controlo de slippage por intenção operacional;
- vetor completo de bloqueios ativos;
- modo manutenção com perfil de saída explícito.

Isto eleva o documento para uma baseline funcional mais próxima de uma **Baseline de Engenharia**, com ganhos claros em:
- determinismo;
- sincronização;
- segurança operacional;
- observabilidade;
- rastreabilidade de causa raiz.

---

## 8. Próxima etapa recomendada

Após esta v0.4, a sequência tecnicamente correta passa a ser:

1. **ODIN-CORE-STATE-AND-EVENT-MODEL.md**
2. **SDS-100 — CORE**
3. **ODIN-TRACEABILITY-MATRIX.md**

---

## Nota de governação da v0.5

A presente versão deve ser tratada como **baseline funcional consolidada**.  
A partir deste ponto, o caminho recomendado é:

1. **ODIN-CORE-STATE-AND-EVENT-MODEL.md**
2. **ODIN-TRACEABILITY-MATRIX.md**
3. **SDS-100 — CORE**
4. SDS temáticos seguintes

A próxima evolução recomendada do FSD já não é nova adenda funcional, mas sim:
- **v1.0 normalizada**, com integração completa dos reforços no corpo principal e limpeza de redundâncias editoriais.

