# ODIN Autonomous DEMO RC2 — Recovery Evidence

Data: 2026-08-29  
Branch: `feature/autonomous-demo-operations-rc2`

## Provas executadas

### Single instance

- A tarefa `ODIN Autonomous Demo Operations RC2` foi iniciada enquanto já estava
  `Running`.
- PID antes: `18968`.
- PID depois: `18968`.
- Resultado: `PASS`; `IgnoreNew` + mutex impediram uma segunda instância lógica.

### Restart do supervisor

- Tarefa parada e cadeia RC2 exata terminada apenas com zero posições e zero
  ordens comprovadas.
- Tarefa reinstalada sem password, privilégios limitados e iniciada novamente.
- Heartbeat retomou e passou a publicar cada novo checkpoint.
- Estado final: `WAITING_MARKET`; `broker_submission_called=false`.
- Resultado: `PASS`.

### Controlo real pelo Task Scheduler

- O caminho antigo via Python do venv deixava dois processos pai/filho vivos
  depois de `Stop-ScheduledTask`; o teste foi classificado como falha real.
- A tarefa passou a executar diretamente o Python base indicado no
  `pyvenv.cfg`, mantendo o `site-packages` MT5 local sem instalação nem PATH.
- Após a correção: estado da tarefa `Ready`, processos RC2 após stop `0`;
  depois do start, tarefa `Running`, processos RC2 `1`, checkpoint `bf14f19`.
- Resultado: `PASS`; o scheduler controla agora o processo real.

### Restart do TradeDesk/Cockpit

- O processo WSL do dashboard foi terminado de forma controlada.
- `Start-ODIN-Dashboard-Persistent.ps1` iniciou uma nova instância.
- `http://127.0.0.1:8765/health` voltou a HTTP 200.
- A rota `/operations/autonomous-demo` expôs métricas e Hermes-versus-Reality.
- Resultado: `PASS`.
- Revalidação no checkpoint `cf5112c`: o listener anterior foi terminado e o
  watchdog recuperou `127.0.0.1:8765` com novo PID, ambas as páginas HTTP 200,
  resource gate e painéis RISK/EXECUTION visíveis.
- Revalidação no checkpoint `06d4023`: o listener foi terminado apenas com
  `SIGTERM` e recuperado pelo launcher bounded. Health, TradeDesk e Cockpit
  voltaram a HTTP 200; o TradeDesk expôs o cartão `Analysis` e a rota
  `/operations/autonomous-demo` publicou `ANALYZED/SCORED`, sem posições,
  ordens ou submissão ao broker.

### Resource guardian

- Probe real: GPU Quadro M4000 38–39 °C, 23/8192 MB VRAM, WSL ativo, FD soft
  limit 10240, uma instância lógica, RAM e disco acima dos mínimos.
- Temperatura CPU não é exposta por `MSAcpi_ThermalZoneTemperature`; o estado é
  `WARNING=cpu_temperature_telemetry_unavailable`, sem valor inventado.
- Testes offline provam BLOCK a 80 °C, sem telemetria térmica total, WSL offline,
  memória/disco críticos e instância lógica duplicada.
- A falha intermitente `resource_probe_unavailable` foi reproduzida com o probe
  PowerShell a bloquear em chamadas WSL aninhadas. A correção separou o probe
  Windows do subprobe WSL, que passou a ter processo e timeout próprios de 10 s.
- Cinco ciclos reais consecutivos observaram WSL em 234--625 ms, uma instância
  lógica, zero exposição e gate sem BLOCK. Um timeout futuro do subprobe continua
  fail-closed com reason code específico.

### Integridade do incident ledger

- Durante uma limpeza de namespace Windows/WSL, o ficheiro JSONL de incidentes
  foi acidentalmente truncado. A ocorrência foi registada explicitamente como
  `INCIDENT_LEDGER_ACCIDENTAL_RESET`; não foi ocultada.
- A linha que existia depois do reset foi preservada em
  `D:\ODIN_LOCAL\reports\recovery\autonomous_demo_incidents_after_accidental_reset_20260829T143916Z.jsonl`
  com SHA-256
  `6b49075f15994b22bcfcc6e657145d435c869adf559dd30ee9a471031af679c6`.
- O ledger foi reconstruído a partir da saída JSONL exata anteriormente
  observada e da semântica determinística de append. Os registos recuperados
  têm marcadores `recovered_after_accidental_reset=true` e `recovery_basis`;
  o supervisor continuou depois a acrescentar incidentes normalmente.

### Hermes-versus-Reality

- O adapter local bounded processa no máximo um trigger novo por ciclo e não tem
  autoridade sobre Strategy, Risk ou execução.
- O primeiro trigger do canary terminou em `MODEL_TIMEOUT` e não foi repetido.
  Saídas truncadas ou placeholders de schema passaram a ser rejeitadas.
- A última prova real no checkpoint `06d4023` produziu uma claim factual para
  `nested_wsl_probe_blocked_parent`, classificada `CONFIRMED`, em 2,344 s.
- As quatro claims anteriores classificadas `CONTRADICTED/HALLUCINATION` foram
  preservadas como evidência; não foram apagadas para melhorar métricas.

### Regressão pré-soak

- Matriz direcionada RC2: `206 passed, 3 subtests passed`.
- Suite completa sem exclusões mais recente: `853 passed, 42 subtests passed`
  em 623,89 s,
  com file descriptor soft limit 8192.
- Ruff global: PASS. Mypy dirigido: PASS nos módulos fonte alterados.
- Parse PowerShell: PASS nos três scripts RC2 alterados. `git diff --check`: PASS.
- Este resultado é validação pré-soak; a suite final continua a ter de ser
  repetida depois dos gates operacionais de 24 h e cinco trades.

### Supervisor visível no TradeDesk

- O checkpoint `7fa5ccd` tornou explícitos na Visão Geral: uptime, ciclo,
  próximo check, branch, checkpoint e último repair.
- Validação no browser local confirmou os seis campos com dados vivos, além de
  `SUPERVISOR RUNNING`, `MARKET CLOSED / WAITING`, `MT5 CONNECTED`,
  `HERMES AVAILABLE` e zero erros de consola.
- A alteração é exclusivamente read-only e de apresentação; não adiciona
  endpoints de controlo nem capacidade financeira.

### Repairs auditáveis e deduplicados

- O checkpoint `8e29e0b` passou a guardar, para cada repair novo, evidence hash,
  root cause, tentativas, ficheiros, testes, estado antes/depois e checkpoint.
  O auto-restart bounded do dashboard gera o mesmo registo estruturado.
- O checkpoint `8687728` adicionou anotações append-only: enriquecem um
  fingerprint histórico sem reescrever o ledger, aumentar `occurrences` ou
  alterar `last_seen`. O relatório usa apenas o registo mais recente de cada
  fingerprint.
- Antes das anotações foi preservado
  `D:\ODIN_LOCAL\reports\recovery\autonomous_demo_incidents_before_repair_annotations_20260829T155328Z.jsonl`
  com SHA-256
  `d25b2fe63477003e1a0b3653fffb882a13f8ea6226f6ceae97453e66bf90cb9b`.
- O relatório vivo final contém seis repairs únicos; todos os seis têm evidence
  hash, ficheiros, testes e estados antes/depois. `NOT_RECORDED=0`.
- O checkpoint `2a93d4e` distingue automaticamente `NEW`, `RECURRING` e
  `REGRESSION`; uma ocorrência posterior a um fix deixa de ser classificada
  incorretamente como nova.

### Curva financeira e recovery autónomo do dashboard

- O checkpoint `3c7dfdc` substituiu o gráfico principal de replay por uma curva
  source-backed de balance/equity MT5 DEMO reconciliados. As amostras têm grain
  de cinco minutos, limite bounded de 2.016 pontos e origem explícita; replay é
  apenas fallback rotulado quando a série real está vazia.
- Primeira amostra viva: balance `49999.12`, equity `49999.12`, zero posições e
  zero ordens. O endpoint e o HTML expuseram a série e o rótulo DEMO.
- O listener do dashboard foi terminado por PID exato e não foi chamado nenhum
  launcher manual. O supervisor observou o outage e recuperou uma única cadeia
  em 34,8 s.
- O incidente `DASHBOARD_RECOVERY` passou de uma para duas ocorrências reais,
  ficou `RESOLVED` e registou fix, ficheiro, teste, estado antes/depois e
  checkpoint. `broker_submission_called=false` durante todo o teste.

### Timeline real do Execution Ledger

- O checkpoint `4bce696` expôs no endpoint read-only uma projeção bounded dos
  últimos 20 eventos, apenas quando a hash-chain do Execution Ledger é válida.
- A timeline viva contém 11 eventos e cobre `PROPOSED`, `RISK_APPROVED`,
  `ORDER_CHECKED`, `FILLED`, `RECONCILED` e `CLOSED`.
- O último evento foi observado como `CLOSED / RECONCILED`, `close_reason=SL` e
  `realized_pnl=-0.88`. O ticket aparece apenas como `••••7246`; não existe chave
  com o ticket integral no payload.
- Testes dirigidos do ledger, Demo Gate, observabilidade e TradeDesk:
  `95 passed`. Ruff e mypy dirigidos: PASS.

### Renderização da curva MT5 DEMO

- A validação no browser detetou que o primeiro path SVG emitia comandos `L`
  sem pares x/y completos, embora os dados fossem corretos.
- O checkpoint `de289fd` passou a construir paths line/area com comandos
  explícitos `M x y` e `L x y`; não houve alteração de dados ou métricas.
- Revalidação renderizada: line e area válidas, label `MT5 DEMO equity`, valor
  `49999.12 EUR`, timeline com 10 linhas, guardrails false e zero erros de
  consola. Testes dirigidos: `12 passed`; Ruff e mypy: PASS.

### Restart do WSL

- Pré-condições: zero posições, zero ordens, mercado stale e nenhuma submissão.
- `Ubuntu-ODIN` foi terminado de forma controlada.
- O supervisor Windows manteve o mesmo PID `18968`.
- Heartbeat avançou de `2026-08-29T12:33:23.694781Z` para
  `2026-08-29T12:33:58.564723Z`.
- O watchdog reergueu WSL e o dashboard voltou a HTTP 200.
- Estado final: `WAITING_MARKET`, checkpoint `ae5be45` e
  `broker_submission_called=false`.
- Resultado: `PASS`.

## Testes não forçados

### Regressão do probe e retoma bounded em 2026-08-29

- A regressão real apresentou `resource_probe_timeout` aos 45 s e transitou
  corretamente para `EXECUTION_PAUSED`, sempre com zero posições, zero ordens e
  `broker_submission_called=false`.
- O bootstrap do supervisor também revelou uma dependência recuperável de
  `wsl.exe ... git rev-parse`; o checkpoint passou a ser lido diretamente dos
  metadados Git locais, de forma determinística e fail-closed (`5a4d544`).
- Os subprocessos de telemetria passaram a ser criados sem consola herdada
  (`87956fa`). A validação dirigida totalizou `25 passed`; Ruff, mypy dirigido e
  `git diff --check` passaram.
- A retoma final em monitorização direta produziu três ciclos consecutivos em
  `WAITING_MARKET`, com resource gate `WARNING`, probe `OK`, WSL em 234--485 ms,
  MT5 ligado, reconciliação `RECONCILED` e os três guardrails a `false`.
- O canal `Microsoft-Windows-TaskScheduler/Operational` estava desativado e o
  utilizador não elevado recebeu `ACCESS_DENIED` ao tentar ativá-lo; não foram
  alteradas permissões nem privilégios. A tarefa mantém `InteractiveToken` e
  `RunLevel=LeastPrivilege`, conforme o contrato de segurança do Windows.
- Evidência histórica mostrou que o wrapper CMD chegara a iniciar o supervisor.
  Uma revalidação limpa do mesmo caminho alcançou `SUPERVISOR_STARTING`, mas o
  filho criado no contexto do Scheduler não publicou heartbeat e voltou a
  bloquear no probe de recursos. A documentação oficial da Microsoft também
  classifica `\\wsl.localhost` como acesso 9P lento, apropriado para acesso
  ocasional e não para loops apertados.
- O ramo experimental foi encerrado e revertido nos checkpoints `7fe3ce5` e
  `4994f3c`; a definição anterior ficou instalada mas não voltou a ser executada.
  Uma única instância direta independente retomou `WAITING_MARKET`, probe `OK`,
  zero exposição e checkpoint alinhado. O autoarranque após reboot continua
  pendente, requer evidência administrativa/logon nova e impede acceptance.
- Uma tarefa one-shot provou que o probe completo pode terminar no Scheduler com
  `LastTaskResult=0`, mas a latência é altamente variável. A medição por componente
  observou `nvidia-smi=13.339 s`, consulta térmica CPU vazia `=9.799 s`, varredura
  de logs `=3.255 s` e duração total da tarefa `=82.956 s`.
- A consulta térmica CPU, que nunca fornece uma amostra neste host, foi removida
  do ciclo e o estado explícito `cpu_temperature_telemetry_unavailable` foi
  preservado (`4153f4c`). Uma tentativa otimizada posterior não produziu saída em
  100 s, provando que aumentar o timeout não seria determinístico; o limite de
  45 s foi reposto em `840569d`.

### Evidência operacional do Task Scheduler e contenção do state writer

- Depois da ativação administrativa do canal
  `Microsoft-Windows-TaskScheduler/Operational`, uma única reprodução iniciou a
  ação esperada: eventos 129/200, instância
  `{fe199c3b-86e2-4f14-a923-86bd4efea422}`, Python PID `15448`, utilizador
  interativo `DESKTOP-4JKDGKS\ODIN`, mesma sessão dos terminais MT5 e módulo
  oficial MetaTrader5 carregado. O Scheduler não falhou a criação do processo.
- A instância não publicou o primeiro heartbeat e foi terminada de forma
  controlada uma única vez. Os eventos 330/201/102/111 registaram a ação do
  operador e o retorno `2147943691` (`ERROR_CANCELLED`); não houve retry nem
  submissão ao broker.
- Ao restaurar o supervisor direto surgiu evidência adicional precisa: no
  segundo ciclo, `Path.replace` recebeu `PermissionError [WinError 5]` ao trocar
  atomicamente `autonomous_demo_state.json.tmp` pelo snapshot lido em paralelo.
  O writer passou a repetir apenas esta substituição, no máximo quatro vezes,
  com backoff total máximo de 300 ms; contenção persistente continua a propagar
  o erro e a falhar fechado.
- Testes novos provam recuperação após uma contenção transitória e falha depois
  do limite sem substituir o último snapshot íntegro. A matriz dirigida passou
  com `54 passed`; Ruff, mypy dirigido e `git diff --check` passaram.
- Uma retoma direta sob leitura concorrente completou três ciclos consecutivos
  em `WAITING_MARKET`, com zero posições, zero ordens, reconciliação
  `RECONCILED`, `broker_submission_called=false` e os três guardrails globais a
  `false`. A validação do autoarranque agendado permanece pendente; esta
  evidência não permite ainda atribuir todo o stall inicial à contenção do
  ficheiro.
- Uma sonda mínima no mesmo token do Scheduler provou que o IPC MT5 não é o
  bloqueio: `initialize` terminou em 47 ms, conta DEMO, broker
  `OANDA TMS Brokers S.A.`, servidor `OANDATMS-MT5`, símbolo disponível e código
  de retorno 0, sem credenciais nem chamadas financeiras.
- A sonda de imports válida mediu `66.610 ms` para carregar a cadeia RC2 a partir
  de `\\wsl.localhost`; `odin.reporting.autonomous_demo_reports` consumiu
  `42.172 ms`. A mesma cadeia, copiada sem `.env` para `D:`, terminou em
  `18.688 ms`; o módulo de relatórios caiu para `6.688 ms`.
- A causa do stall agendado foi assim classificada como bootstrap Python
  altamente variável sobre 9P/UNC, não falha do Scheduler nem do MT5. O
  instalador passou a criar um bundle local imutável por checkpoint, com
  inventário SHA-256 e manifesto disarmado, enquanto `.env`, configuração e Git
  permanecem na fonte canónica WSL. A tarefa conserva um único processo Python
  rastreável através de um bootstrap local sem capacidade financeira.
- O primeiro arranque do bundle local publicou heartbeat e completou três ciclos
  no mesmo PID/checkpoint, mas o probe PowerShell filho excedeu 45 s em todos os
  ciclos e manteve `EXECUTION_PAUSED`. O timeout não foi aumentado.
- O probe Windows foi substituído por um subprocesso Python stdlib isolado. Usa
  `GetSystemTimes`, `GlobalMemoryStatusEx`, `GetProcessHandleCount`, espaço em
  disco, `nvidia-smi` bounded e verifica o mutex singleton já adquirido; WSL
  continua num subprobe separado. A primeira medição real terminou em 1.484 ms,
  reportou GPU a 39 °C, RAM/disco suficientes e uma instância lógica. Telemetria
  ausente ou timeout continuam a produzir BLOCK.
- O bundle `7f62db7178ad` foi iniciado pelo Scheduler como PID `18600`; os eventos
  operacionais 130--134 provam fila, instância, processo e ação esperados. O
  primeiro heartbeat chegou no ciclo 1 e o mesmo PID completou três ciclos.
  Todos ficaram em `WAITING_MARKET`, resource gate `WARNING`, probe `OK`, WSL em
  2.953--4.016 ms, zero posições, zero ordens, reconciliação preservada,
  `broker_submission_called=false` e guardrails globais `false`.
- A telemetria Hermes, que corre dentro do WSL e não aparece em `tasklist.exe`,
  foi incorporada no subprobe WSL já existente através de um marcador booleano,
  sem guardar argumentos de processos. A duração de probes Windows bem-sucedidos
  passou também a ser persistida. A matriz dirigida desta alteração passou com
  `57 passed`; Ruff, mypy dirigido e `git diff --check` passaram.
- A validação seguinte mostrou que, neste host, Hermes é a aplicação Windows
  `Hermes.exe` e Ollama também corre no Windows; `tasklist.exe` expirava no token
  agendado e devolvia ambos como falsos. O subprocesso foi removido e os nomes
  passaram a ser enumerados diretamente por `CreateToolhelp32Snapshot`. A sonda
  real terminou em 622 ms e observou `hermes_running=true` e
  `ollama_running=true`; não foram iniciados serviços nem guardados argumentos.
- No merge seguinte, o marcador factual `HERMES:0` do WSL sobrescreveu
  incorretamente `Hermes.exe=true` do Windows. As fontes passaram a permanecer
  separadas (`wsl_hermes_running`) e `hermes_running` é a união explícita das
  observações Windows/WSL. Ollama já foi confirmado `true`; o runtime manteve
  quatro ciclos em `WAITING_MARKET`, probe `OK` em 1.125--4.250 ms, resource
  `WARNING`, zero exposição e guardrails `false` durante o diagnóstico.
- Um crash controlado do processo da ação revelou que `RestartCount=3` não é
  acionado por esse exit: eventos 198/199 registaram retorno `0xFFFFFFFF` como
  conclusão da tarefa, que ficou `Ready`. O runtime foi restaurado manualmente
  uma vez, sem exposição. O bootstrap passou por isso a supervisionar um único
  filho real, com relançamentos bounded 5/30/60 s e ledger watchdog disarmado;
  quatro falhas consecutivas esgotam o orçamento e terminam fail-closed.
- A validação real do watchdog local no bundle `5a4527a5643a` iniciou o bootstrap
  PID `19720` pelo Task Scheduler (eventos Operational 110/129/200), terminou
  controladamente apenas o supervisor filho PID `11092` e preservou o pai. O
  watchdog registou `SUPERVISOR_RESTART_SCHEDULED`, `restart_attempt=1` e
  `restart_delay_seconds=5`; o novo filho PID `16580` iniciou 5,9 s depois e
  retomou heartbeat no ciclo 1. Não existiam posições nem ordens, a
  reconciliação permaneceu íntegra, `broker_submission_called=false` e os três
  guardrails globais permaneceram `false`.
- Num ciclo posterior, o subprobe WSL excedeu isoladamente o timeout bounded de
  10 s e produziu `EXECUTION_PAUSED` / `wsl_runtime_unavailable`. Sem qualquer
  retry externo ou relaxamento do gate, o ciclo seguinte observou novamente o
  WSL, recuperou para `WAITING_MARKET` e manteve resource gate `WARNING`. Esta é
  a recuperação fail-closed pretendida; o mercado continuava stale/fechado e
  nenhuma submissão ao broker ocorreu.
- A recorrência do timeout foi separada de indisponibilidade factual do WSL: no
  mesmo período, o TradeDesk alojado no WSL manteve `/health` em HTTP 200 e a
  sonda idêntica respondeu diretamente em 522--615 ms. O resource gate passou a
  aceitar apenas a combinação exata `wsl_resource_probe_timeout` + dashboard
  ODIN já observado como `RUNNING` como evidência de runtime vivo, preservando o
  timeout e marcando `wsl_resource_telemetry_degraded` como `WARNING`. Sem esse
  healthcheck atual, WSL falso/desconhecido continua `BLOCK`. Testes dirigidos:
  `61 passed`; Ruff, mypy no módulo tipado alterado e `git diff --check`: PASS.
- A primeira rotação controlada após o checkpoint confirmou ainda que
  `Stop-ScheduledTask` terminava o bootstrap, mas deixava o supervisor filho
  órfão. Com posições/ordens a zero e sem submissão ao broker, esse único PID foi
  terminado de forma controlada. O bootstrap passou a colocar cada filho num
  Windows Job Object com `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`; se a contenção não
  puder ser configurada, termina o filho e regista
  `SUPERVISOR_CHILD_CONTAINMENT_FAILED` em vez de o deixar correr sem watchdog.
  A matriz dirigida passou com `62 passed`; Ruff, mypy dirigido, compilação do
  bootstrap e `git diff --check`: PASS.
- O bundle imutável `646e7f2b7717` (inventário SHA-256
  `BA41E383D591A386E329C8458667FC27BEC0A825E9A1A8B6CE90757FA17ABE91`) foi
  instalado e validado no Task Scheduler. Numa única rotação controlada, o
  evento Operational 330 terminou o bootstrap PID `2736` e o Job Object terminou
  também o supervisor PID `18184`, sem intervenção adicional. A retoma produziu
  eventos 110/129/200, bootstrap PID `17096` e novo supervisor PID `17456`.
  Três ciclos consecutivos ficaram em `WAITING_MARKET`, resource `WARNING`, WSL
  vivo, zero posições/ordens, reconciliação `RECONCILED`, nenhuma submissão ao
  broker e guardrails globais `false`.
- Um incidente único posterior expôs a mesma contenção Windows no writer dos
  relatórios: `AUTONOMOUS_REPORTING_EXCEPTION / PermissionError` enquanto um
  leitor abria os artefactos. O writer de estado já tinha retry bounded, mas
  `_atomic_text` ainda fazia uma única substituição. Os relatórios passaram a
  repetir apenas o `replace`, no máximo quatro vezes, com esperas de
  50/100/150 ms; contenção persistente conserva o relatório anterior e propaga a
  falha. A validação dirigida passou com `67 passed`; Ruff, mypy dirigido e
  `git diff --check`: PASS.
- O bundle `d02af7bf9c6b` foi instalado após uma rotação limpa do Job Object e
  publicado no Task Scheduler com inventário SHA-256
  `3FE4C4E1609323AD186E09975ACE72C670E5CD0636651B904835D19CF8C8DFCF`.
  Uma prova live fez 4.007 leituras concorrentes durante vários ciclos: houve
  uma contenção visível no leitor e zero novas exceções do writer. O incidente
  foi anotado canonicamente como resolvido por
  `bounded_report_atomic_replace_retry`; a reparação apareceu em
  `ODIN_AUTONOMOUS_DEMO_REPAIRS.md`. O supervisor permaneceu em
  `WAITING_MARKET`, sem posições/ordens ou submissão ao broker.
- A auditoria da superfície operacional encontrou um atalho manual legado que
  ainda chamava `Read-ODIN-MT5-Demo.ps1` e podia publicar observações da
  instalação MetaQuotes-Demo excluída. Nenhuma tarefa agendada ou launcher RC2
  usava essa instalação, mas o atalho podia criar ambiguidade visual. O refresh
  manual passou a validar apenas o estado/heartbeat persistente do supervisor
  OANDA allowlisted; o collector legado permanece apenas como artefacto
  histórico e saiu do caminho ativo. A matriz RC2 alargada passou com
  `222 passed, 20 subtests`; a alteração dirigida passou com `55 passed`, Ruff,
  parser PowerShell, validação live `-ValidateMt5Only` e `git diff --check`.
- O bundle `06166ab61e3f` foi instalado com inventário SHA-256
  `64355B421CE6FC898B0BE6A1F0792F5642A30647CDED80BB1AEADD69BA8B71D0`;
  o refresh instalado tem SHA-256
  `66B38726C73C8FC54BB24961195D642BC36BF4D84186B07FB8520C8558763964`.
  O atalho genérico `MetaTrader 5.lnk` passou a apontar para a instalação OANDA
  allowlisted e a auditoria recursiva do Desktop encontrou zero atalhos para
  `D:\ODIN_LOCAL\mt5\terminal64.exe`. O processo/instalação MetaQuotes não foi
  terminado nem apagado; ficou apenas fora do caminho operacional.
- A auditoria live do Cockpit mediu `/operations/overview` em 28.053 s e
  encontrou `sqlite3.OperationalError: database is locked`: cada GET voltava a
  executar a inicialização de schema e múltiplas instâncias do store escreviam
  em paralelo no mesmo ficheiro. O store passou a partilhar um `RLock` por
  caminho dentro do processo, a inicializar schema/WAL uma vez e a preservar
  todas as escritas de auditoria; a rota deixou de reinicializar SQLite em cada
  pedido. Testes dirigidos: `37 passed`; Ruff e `git diff --check`: PASS. Os três
  erros mypy preexistentes em `upsert_hermes_goal` foram reproduzidos no
  checkpoint anterior e não foram alterados por esta correção.
- O lock de SQLite ficou resolvido, mas duas medições seguintes ainda excederam
  15 s. O profiling separou a causa restante: sobre o log/SQLite live,
  `observation_frame_status` consumia 6,243 s e o Cockpit voltava a chamar
  `/operations/overview` a cada 30 s, reexecutando o pipeline técnico e gerando
  auditoria recursiva. O Cockpit deixou de fazer esse polling automático e
  passou a compor `Live operational summary` exclusivamente com o estado RC2,
  heartbeat, Risk, Execution e recursos já persistidos. O endpoint técnico
  continua disponível para diagnóstico explícito. Testes dirigidos:
  `17 passed`; Ruff, mypy dirigido, compilação e `git diff --check`: PASS.
- Uma página Cockpit carregada antes do deploy continuou a chamar o endpoint
  legado a cada 30 s, provando que a correção apenas no cliente não era
  suficiente. `/operations/overview` deixou por isso de reconstruir Market,
  Observation Frame, Strategy, Risk e Hermes a cada GET. A compatibilidade do
  schema foi preservada, mas todos os campos passam a ser projetados a partir
  do snapshot e heartbeat persistentes do supervisor RC2. Um teste de regressão
  prova que uma leitura produz apenas os dois eventos de request/response e não
  reexecuta pipelines. Testes dirigidos: `18 passed`; Ruff: PASS.
- No deploy live, o overview passou de 11,955 s para 0,186 s e de centenas de
  eventos para exatamente dois (`dashboard.request.received` e
  `dashboard.state.served`). O healthcheck recorrente foi também tornado puro:
  deixou de chamar `validate_runtime()` apenas para devolver as duas flags
  bloqueadas. A regressão dirigida passou com `21 passed`; Ruff, mypy isolado e
  `git diff --check`: PASS. A auditoria anterior foi movida sem perda para
  `D:\ODIN_LOCAL\archives\dashboard-audit-20260829T2325Z`; `PRAGMA quick_check`
  devolveu `ok` e os hashes SHA-256 preservados são
  `F5CDF23778EE0EEE8677A453777759688AA2FB11A8723570F02B55C4BB19B502`
  (JSONL) e
  `6E74895948C9730955330E823A7FC65C8C0B7926E80E51B8C6B0539448FDFC95`
  (SQLite).
- O bundle imutável `25fb4e107ebc` foi instalado com inventário SHA-256
  `587FACDB27E9703C6C6F441F9FDDD05C808863BA3BADA665A6EBACCAB2B2BAE4`.
  O Task Scheduler Operational está `Enabled` e registou os eventos 110/129/200
  do arranque atual. O supervisor permaneceu `WAITING_MARKET` durante oito
  ciclos observados, com conta DEMO OANDA allowlisted, terminal e Algo Trading
  disponíveis, tick stale de fim de semana, zero posições/ordens,
  `RECONCILED` e nenhuma submissão ao broker. A matriz RC2 alargada passou com
  `229 passed in 13.38s`; Ruff e `git diff --check`: PASS.
- A telemetria de storage contava apenas `D:\ODIN_LOCAL` e omitia o JSONL/SQLite
  ativos do dashboard no WSL. O bundle `256f6182a3ff` (inventário SHA-256
  `7C62B867EEB49B36DE678D9933BC8B771CAE61D5014E979A1E0A2A2E1A545D49`)
  passou a preservar e somar as duas origens. A prova live observou
  `4.033.420 = 1.276.979 Windows + 2.756.441 WSL` bytes de logs/reports e
  `2.625.536 = 90.112 Windows + 2.535.424 WSL` bytes SQLite, com probe WSL em
  359 ms. O supervisor manteve `WAITING_MARKET`, zero exposição e guardrails
  `false`. Matriz RC2: `232 passed in 14.08s`; Ruff, mypy dirigido e
  `git diff --check`: PASS.
- O relatório runtime de Acceptance resumia apenas soak, trades e ledgers, sem
  tornar explícitos os restantes gates da Definition of Done. O checkpoint
  `856e3f8` substituiu esse resumo por uma matriz requisito a requisito e
  preservou o fecho fail-closed: atingir `24h` e `5` trades produz apenas
  `ELIGIBLE_FOR_FINAL_AUDIT`; nunca `PASSED` automático. O bundle imutável
  `856e3f8fb130` foi instalado com inventário SHA-256
  `506C05927C65B952E55D1A2B3FC1F18D8B82AC81187A26B6C2BE1CC2EDDE50E7`.
  A prova live confirmou `Status: NOT_READY`, TradeDesk/Cockpit `PASS`, uma
  instância do supervisor, zero posições/ordens e guardrails `false`. Validação:
  `41 passed` dirigidos, matriz RC2 de `213 passed in 19.54s`, Ruff, mypy
  isolado e `git diff --check`: PASS. A correção ficou registada no
  Incident/Repair Ledger como `ACCEPTANCE_EVIDENCE_GAP` resolvido por
  `requirement_by_requirement_fail_closed_acceptance_matrix`.
- A validação visual live encontrou uma decisão Shadow histórica (`BUY`,
  `2026-07-31T22:15:00Z`, `FRESH`) apresentada no cartão principal quando o
  supervisor não possuía decisão live e estava em `WAITING_MARKET`. O checkpoint
  `1a6cb97` removeu esse fallback silencioso: o cartão passou a chamar-se
  `Decisão live ODIN` e, na ausência de uma decisão autónoma factual, projeta
  apenas o estado runtime atual sem criar uma entrada no Decision Ledger. A
  prova no browser mostrou `EURUSD · LIVE`, `BLOCKED`, fonte `RUNTIME_STATE`,
  `market_closed_or_stale` e `STALE`; Shadow/replay permaneceu explicitamente
  separado com a sua freshness histórica. Risk continuou `BLOCK`, execução
  `NO_ORDER`, reconciliação `RECONCILED`, submissão ao broker `false`, zero
  posições/ordens e guardrails `false`. Validação: `19 passed`, Ruff, mypy
  isolado, sintaxe JavaScript, browser live e `git diff --check`: PASS. Repair
  registado como `DASHBOARD_LIVE_REPLAY_SEPARATION`.
- A continuação da auditoria visual encontrou o `Risk=ALLOW_DEMO` do canary no
  painel técnico de Execution Ledger sem uma indicação explícita de que era
  evidência histórica. O checkpoint `24d4cbd` tornou o contrato aditivo e
  auditável: o payload declara
  `evidence_scope=HISTORICAL_EXECUTION_LEDGER_AND_CANARY`, marca decisão e Risk
  como `HISTORICAL_LEDGER_RECORD` e referencia `/operations/autonomous-demo`
  como autoridade runtime atual. O Cockpit passou a rotular Shadow, auditoria
  MT5 e ledger como históricos, mantendo o `Live operational summary`
  explicitamente separado. A prova no browser confirmou simultaneamente
  histórico `ALLOW_DEMO`, live `Risk=BLOCK`, execução `NO_ORDER`, submissão
  `false`, guardrails `false` e zero erros de consola. Validação: `19 passed`,
  Ruff, mypy isolado, sintaxe JavaScript, browser live e `git diff --check`:
  PASS. Repair registado como `COCKPIT_LIVE_HISTORICAL_SCOPE`.
- O controlo `OPEN REPORTS` apontava para `/cockpit#reports`, mas o Cockpit não
  possuía esse destino. O checkpoint `9680f4d` adicionou um inventário local
  estritamente read-only com os oito relatórios RC2 obrigatórios, expondo apenas
  nome, disponibilidade, bytes e timestamp; nenhum conteúdo de relatório é
  devolvido. A prova end-to-end no browser abriu o link, encontrou o anchor
  `#reports`, carregou `8/8`, confirmou `read_only=true`, guardrails `false` e
  zero erros de consola. Validação: `20 passed`, Ruff, mypy isolado, sintaxe
  JavaScript, browser live e `git diff --check`: PASS. Repair registado como
  `OPERATOR_REPORTS_NAVIGATION`.
- Os controlos do operador foram exercitados com mercado stale, zero
  posições/ordens e reconciliação `RECONCILED`. `PAUSE DEMO EXECUTION` foi
  acionado no browser e o ciclo seguinte entrou em `EXECUTION_PAUSED` com
  `operator_pause`. O botão `RESUME` apresentou a confirmação visual obrigatória;
  o pedido confirmado pelo endpoint local foi aceite e revalidou todos os gates,
  regressando a `WAITING_MARKET` por `market_closed_or_stale`. O mesmo contrato
  local recebeu `SAFE_STOP`, produziu `EXECUTION_PAUSED` com
  `operator_safe_stop`, e um novo `RESUME` confirmado regressou a
  `WAITING_MARKET`. A automação do browser não conseguiu concluir o click de
  SAFE STOP devido a timeout do próprio browser; por isso a evidência desse
  botão é a ligação estática ao mesmo endpoint mais o teste factual do endpoint,
  não uma declaração de click end-to-end. Em todas as transições: submissão ao
  broker `false`, zero exposição, `safe_to_trade=false`, `real_trading=false` e
  `execution_allowed=false`.
- O canal `Microsoft-Windows-TaskScheduler/Operational` permanece `Enabled` e
  registou a instância corrente às `2026-08-30T00:00:32+01:00`: eventos
  325/110/129/100/200, bootstrap PID `516` e ação Python direta no bundle
  imutável `856e3f8fb130`. O bootstrap mantém um único supervisor lógico, PID
  `3152`; o heartbeat correlacionado avançou até ao ciclo 73, ficou fresh e
  publicou `WAITING_MARKET`. Os quatro endpoints locais responderam HTTP 200.
  Esta instância começou depois de uma atualização da tarefa, não depois de um
  reboot; por isso não é usada como prova de autoarranque após Windows restart.
- A auditoria de processos encontrou simultaneamente o terminal histórico
  `D:\ODIN_LOCAL\mt5\terminal64.exe` e o terminal OANDA allowlisted. O estado
  factual do supervisor identifica exclusivamente
  `C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe`, conta `DEMO`, broker
  `OANDA TMS Brokers S.A.`, server `OANDATMS-MT5`, zero posições/ordens e
  reconciliação `RECONCILED`. Nenhum processo foi terminado ou reconfigurado; a
  instância histórica continua apenas fora do caminho operacional.
- A auditoria read-only dos artefactos confirmou os oito relatórios RC2
  obrigatórios e `docs/ODIN_NOTION_SYNC_2026-08-29.md`. O Execution Ledger tem
  11 registos, cadeia `OK`, zero anomalias, um lifecycle fechado e zero erros de
  reconciliação; o Decision Ledger tem um registo e cadeia `OK`. O ficheiro
  `ODIN_AUTONOMOUS_DEMO_TRADES.jsonl` está vazio por desenho: o canary RC1
  permanece integralmente no Execution Ledger, mas é excluído do relatório de
  trades autónomos RC2, cuja contagem factual continua zero.
- O registo autoritativo Hermes contém 19 analysis events para 19 `trigger_id`
  únicos (um trade fechado, 17 incidentes e um resumo diário), zero triggers
  duplicados, 20 claims e 20 `claim_id` únicos. As 75 linhas de
  `ODIN_HERMES_VS_REALITY.jsonl` são snapshots cumulativos do scorecard quando a
  evidência muda, não 75 chamadas ao modelo; a vista live usa o snapshot mais
  recente. Assim, mantém-se o limite de uma análise por trade/incidente único e
  não foi necessária alteração de código.
- A auditoria de redaction examinou 97 artefactos runtime ativos e 9.960.500
  bytes: relatórios, estado, logs e ledgers Windows, além de
  `logs/hermes_ollama.jsonl`, `logs/odin_events.jsonl` e `runtime/odin.sqlite` no
  WSL. A pesquisa reportou apenas categorias e nomes de ficheiro, nunca valores,
  e encontrou zero ocorrências de token/password OANDA, Bearer credential,
  segredo JSON ou login/account ID não mascarado. `.env`, fontes e bundles foram
  deliberadamente excluídos porque esta prova cobre saídas persistidas.
- A atualização read-only de `2026-09-01` examinou 171 ficheiros textuais ativos
  em `logs`, `reports`, `state` e `runtime` (6.273.547 bytes), além dos ficheiros
  SQLite/DB através de pesquisa binária que devolveu apenas contagens. Não foi
  lido o `.env` nem impresso qualquer valor. Foram encontrados zero ficheiros
  com Bearer token, password JSON, atribuição de password/token OANDA ou
  login/account ID persistido; os SQLite/DB também devolveram zero matches para
  essas categorias.
- Em `2026-09-01`, o terceiro lifecycle autónomo ficou persistido como
  `FILLED/PENDING` sem `position_id`, apesar de o broker já não apresentar
  posições ou ordens. Uma sonda MT5 estritamente read-only encontrou exatamente
  um deal e uma ordem pelos identificadores já guardados no Execution Ledger,
  um único `position_id`, símbolo `EURUSD.pro`, lado BUY, volume de entrada e
  saída `0.01`, `magic` e comentário ODIN coincidentes e histórico integralmente
  fechado. O checkpoint `d492516` passou a recuperar o vínculo apenas quando
  todas essas provas são únicas e coerentes; evidência ausente, ambígua ou
  divergente continua a bloquear. A prova sobre uma cópia temporária passou e a
  retoma em `PAUSE` acrescentou apenas `RECONCILED` e `CLOSED` ao ledger real:
  23 registos, cadeia `OK`, quatro lifecycles DEMO fechados no total, três
  autónomos, zero anomalias, zero duplicados e zero erros de reconciliação.
  Validação: 6 testes de lifecycle, 94 testes adjacentes e sonda real sobre
  ledger temporário; submissão ao broker `false` durante toda a recuperação.
- A mesma retoma revelou um stall transitório depois de o supervisor escrever o
  estado e antes de publicar heartbeat. Hermes sem transporte completou em
  `0.032 s`, reporting completo em `0.046 s` e o transporte Ollama isolado em
  `1.828 s`, provando que o risco estava na chamada opcional síncrona sem um
  limite duro ao nível do processo. O checkpoint `cd3fdc6` isolou apenas o
  transporte Ollama num worker stdlib, remove segredos ODIN do respetivo
  ambiente e termina-o após 55 segundos; timeout passa a `MODEL_UNAVAILABLE` e
  não bloqueia o supervisor. O bundle imutável `cd3fdc6812c6`, inventário
  SHA-256 `78D7E7966605D9313D0DCCD509E71B6EDB5C88A1B4B97A894B679CB66FA42B67`,
  publicou dois heartbeats consecutivos em `EXECUTION_PAUSED/operator_pause` e
  manteve TradeDesk, Cockpit e health em HTTP 200. Validação: 25 testes focados,
  105 testes RC2 adjacentes, Ruff, mypy dirigido, `git diff --check` e worker
  Ollama real em `4.703 s`: PASS.
- Após `RESUME` confirmado, o ciclo live revalidou broker/server DEMO, zero
  posições, zero ordens, mercado aberto, dados `FRESH` e reconciliação
  `RECONCILED`. A execução permaneceu corretamente em `EXECUTION_PAUSED` porque
  `terminal_trade_allowed=false`; o ODIN não alterou automaticamente Algo
  Trading. Submissão ao broker `false` e flags globais `false`.
- A validação integral do checkpoint executou a suite sem exclusões e com
  `ulimit -n 8192`: `885 passed`, `42 subtests`, zero falhas reportadas em
  `602.64 s` (`605.14 s` de tempo externo). Ruff global passou; mypy isolado no
  scope RC2 passou em 15 ficheiros; compilação dos entrypoints Windows e
  `git diff --check` passaram. A expansão não isolada do mypy reproduziu 36
  erros legados em 12 módulos importados fora do scope RC2, sem erro nos
  ficheiros dirigidos e sem alteração de código para esconder dívida histórica.
- Com zero posições e zero ordens, foi executado um único `wsl --shutdown` para
  validar recovery real. O dashboard ficou transitoriamente indisponível e o
  caminho persistente voltou a arrancar a distro sem comando manual de startup.
  A prova pós-recovery observou novo kernel WSL com uptime de aproximadamente
  113 segundos, Task Scheduler `Running`, heartbeat fresco no ciclo 23,
  TradeDesk/Cockpit/health em HTTP 200, reconciliação `RECONCILED` e estado
  `EXECUTION_PAUSED/terminal_trading_not_allowed`. Não houve posição, ordem,
  submissão ao broker ou alteração dos guardrails.

- Restart Windows: não executado nesta sessão para não interromper o operador;
  autoarranque está instalado no Task Scheduler e permanece por validar após um
  reboot humano oportuno.
- Restart/recovery com posição aberta: observado factualmente em `2026-09-01`.
  O processo persistente terminou inesperadamente com o resultado Task Scheduler
  `0xC000013A` enquanto existia uma posição DEMO legítima; a origem concreta do
  encerramento permanece `windows_process_control_exit_origin_unresolved`. A
  posição permaneceu no broker com SL/TP e zero ordens pendentes. Uma única
  retoma controlada da tarefa reconstruiu o estado a partir do MT5, iniciou uma
  única instância bootstrap/supervisor e regressou a `POSITION_MONITOR` com uma
  posição, zero ordens, reconciliação `RECONCILED`, heartbeat fresco e
  TradeDesk/Cockpit/health HTTP 200. Não existiu reenvio, nova submissão ou
  alteração dos guardrails. O incidente está registado como
  `SUPERVISOR_UNEXPECTED_EXIT_DURING_POSITION`; não se inventou uma root cause.
- Resposta perdida de broker: coberta por testes fake/offline; não provocar timeout
  real nem reenviar ordem.

`safe_to_trade=false`  
`real_trading=false`  
`execution_allowed=false`
