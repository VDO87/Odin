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

- Restart Windows: não executado nesta sessão para não interromper o operador;
  autoarranque está instalado no Task Scheduler e permanece por validar após um
  reboot humano oportuno.
- Restart com posição aberta: não executado porque não existe posição e é proibido
  forçar um trade para criar evidência. O recovery path broker-first tem testes
  offline e será observado quando surgir uma posição legítima.
- Resposta perdida de broker: coberta por testes fake/offline; não provocar timeout
  real nem reenviar ordem.

`safe_to_trade=false`  
`real_trading=false`  
`execution_allowed=false`
