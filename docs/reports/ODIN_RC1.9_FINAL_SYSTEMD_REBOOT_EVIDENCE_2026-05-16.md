# ODIN RC1.9 FINAL — Systemd + Reboot Evidence

- Data (UTC): `2026-05-16T11:10:05Z`
- Branch: `release/rc1`
- Commit: `2ce4266`
- Runtime: `~/ODIN_RUNTIME`
- Repositório: `/home/vdo/Secretária/Projects_Codex/Odin_Teste`

## 1) Comandos executados

```bash
git branch --show-current
git status --short --branch
git rev-parse --short HEAD
ls -la ~/ODIN_RUNTIME
ls -la ~/ODIN_RUNTIME/app
grep -E "ENABLE_REAL_TRADING|MT5_ORDER_SEND_ENABLED|BROKER_ALLOW_REAL_EXECUTION" ~/ODIN_RUNTIME/.env || true
sudo systemctl daemon-reload
sudo systemctl enable odin-runtime.service odin-dashboard.service
sudo systemctl start odin-runtime.service odin-dashboard.service
sudo systemctl status odin-runtime.service odin-dashboard.service --no-pager
sudo journalctl -u odin-runtime.service -u odin-dashboard.service -n 100 --no-pager
sudo reboot
sudo systemctl status odin-runtime.service odin-dashboard.service --no-pager
sudo journalctl -u odin-runtime.service -u odin-dashboard.service -b -n 200 --no-pager
cd ~/ODIN_RUNTIME/app
./run_odin.sh --dashboard-qa
./run_odin.sh --tui-once
./run_odin.sh --runtime-validate
grep -E "ENABLE_REAL_TRADING|MT5_ORDER_SEND_ENABLED|BROKER_ALLOW_REAL_EXECUTION" ~/ODIN_RUNTIME/.env || true
```

## 2) Resultado systemd antes do reboot

`sudo systemctl daemon-reload`:

```text
sudo: a terminal is required to read the password; either use the -S option to read from standard input or configure an askpass helper
sudo: a password is required
```

`sudo systemctl enable ...`:

```text
sudo: a terminal is required to read the password; either use the -S option to read from standard input or configure an askpass helper
sudo: a password is required
```

`sudo systemctl start ...`:

```text
sudo: a terminal is required to read the password; either use the -S option to read from standard input or configure an askpass helper
sudo: a password is required
```

`sudo systemctl status ...`:

```text
sudo: a terminal is required to read the password; either use the -S option to read from standard input or configure an askpass helper
sudo: a password is required
```

Sem `sudo`:

```text
Failed to connect to bus: Operation not permitted
```

## 3) Resultado journalctl antes do reboot

`sudo journalctl -u odin-runtime.service -u odin-dashboard.service -n 100 --no-pager`:

```text
sudo: a terminal is required to read the password; either use the -S option to read from standard input or configure an askpass helper
sudo: a password is required
```

Sem `sudo`:

```text
-- No entries --
```

## 4) Resultado reboot real

`sudo reboot`:

```text
sudo: a terminal is required to read the password; either use the -S option to read from standard input or configure an askpass helper
sudo: a password is required
```

Conclusão: reboot real **não executado** neste ambiente.

## 5) Resultado systemctl pós-reboot

Não aplicável, porque o reboot real não foi executado.

Tentativa de recolha:

```text
sudo: a terminal is required to read the password; either use the -S option to read from standard input or configure an askpass helper
sudo: a password is required
```

## 6) Resultado journalctl pós-reboot

Não aplicável, porque o reboot real não foi executado.

Tentativa de recolha:

```text
sudo: a terminal is required to read the password; either use the -S option to read from standard input or configure an askpass helper
sudo: a password is required
```

## 7) Resultado `dashboard-qa`

Resultado: **FAIL** no ambiente actual.

```text
OSError: [Errno 30] Read-only file system: '/home/vdo/ODIN_RUNTIME/dashboard_preview/index.html'
```

## 8) Resultado `tui-once`

Resultado: **PASS** (execução com saída coerente de bloqueio):

- `SAFE_TO_TRADE False`
- `TRADING REAL BLOCKED`
- `ATLAS SHADOW_ONLY`
- comandos perigosos indisponíveis

## 9) Resultado `runtime-validate`

Resultado: **FAIL** no ambiente actual.

```text
OSError: [Errno 30] Read-only file system: 'logs/system/runtime_validation.log'
```

## 10) Confirmação das flags de segurança

Consulta obrigatória em `~/ODIN_RUNTIME/.env`:

```text
grep: /home/vdo/ODIN_RUNTIME/.env: No such file or directory
```

Evidência complementar em templates systemd (`~/ODIN_RUNTIME/app/services/*.service.template`):

- `Environment=ENABLE_REAL_TRADING=false`
- `Environment=MT5_ORDER_SEND_ENABLED=false`
- `Environment=BROKER_ALLOW_REAL_EXECUTION=false`

## 11) Decisão final RC1.9

**FAIL**

## 12) Justificação técnica

Critérios obrigatórios de aprovação RC1.9 não foram cumpridos neste host/sessão:

1. Não foi possível activar/validar `systemd` (sudo interativo indisponível e DBus sem permissão).
2. Reboot real não foi executado.
3. Não há evidência pós-boot de serviços activos.
4. `dashboard-qa` e `runtime-validate` falharam por filesystem read-only no runtime.
5. O ficheiro `~/ODIN_RUNTIME/.env` não existe para validar diretamente as flags obrigatórias.

## 13) Correcções objectivas para novo ciclo RC1.9-FINAL

1. Executar o mesmo procedimento em terminal/host com `sudo` funcional (TTY interativa).
2. Garantir permissões de escrita em `~/ODIN_RUNTIME/dashboard_preview` e `~/ODIN_RUNTIME/logs/system`.
3. Criar/validar `~/ODIN_RUNTIME/.env` com:
   - `ENABLE_REAL_TRADING=false`
   - `MT5_ORDER_SEND_ENABLED=false`
   - `BROKER_ALLOW_REAL_EXECUTION=false`
4. Repetir sequência pré-reboot e pós-reboot, recolhendo `systemctl` e `journalctl -b`.

## 14) FAIL TRIAGE — Runtime write access

### 14.1 Testes de escrita executados

`touch ~/ODIN_RUNTIME/.write_test`:

```text
touch: cannot touch '/home/vdo/ODIN_RUNTIME/.write_test': Read-only file system
```

`touch ~/ODIN_RUNTIME/dashboard_preview/.write_test`:

```text
touch: cannot touch '/home/vdo/ODIN_RUNTIME/dashboard_preview/.write_test': Read-only file system
```

`cd ~/ODIN_RUNTIME/app && mkdir -p logs/system && touch logs/system/.write_test`:

```text
touch: cannot touch 'logs/system/.write_test': Read-only file system
```

Controlo de ambiente (fora do runtime):

- `touch /home/vdo/Secretária/Projects_Codex/Odin_Teste/.codex_write_probe` -> `workspace_write_ok`
- `touch /tmp/.codex_write_probe` -> `tmp_write_ok`

### 14.2 Diagnóstico de filesystem/permissões

- `df -h ~/ODIN_RUNTIME` mostra filesystem raiz com espaço livre (`/` com ~310G livres), logo não é falta de espaço.
- `ls -ld` mostra ownership e permissões normais (`vdo:vdo`, `drwxrwxr-x`) para `~/ODIN_RUNTIME`, `~/ODIN_RUNTIME/dashboard_preview` e `~/ODIN_RUNTIME/app/logs/system`.
- O erro é consistente como `Read-only file system` (errno 30), não `Permission denied`.

Diagnóstico provável:

1. Nesta sessão Codex, `~/ODIN_RUNTIME` está exposto como leitura apenas por política de sandbox do agente.
2. O problema observado aqui é **primariamente do ambiente Codex**, não evidência suficiente de montagem read-only no host real.

### 14.3 Verificação de caminhos e escrita nos scripts

Resultados de pesquisa:

- `apps/dashboard_html/app.py` escreve preview em `dashboard_preview/*.html` via `export_preview()`; sem fallback de escrita.
- `odin_core/runtime_validator.py` escreve em `logs/system/runtime_validation.log` via `log_runtime_validation(...)`.
- `odin_logs/logger.py` escreve diretamente com `open(..., "a")`; sem fallback para `/tmp` nem degradação controlada.

### 14.4 Avaliação de fallback seguro de logs (sem implementar)

Estado atual: **não existe fallback seguro** quando `logs/` não é escrevível.

Comportamento observado:

- Falha de escrita lança exceção `OSError` e interrompe `dashboard-qa` / `runtime-validate`.

### 14.5 Correcções recomendadas para host real (operacionais)

Executar no host real (fora do sandbox Codex):

```bash
ls -ld ~/ODIN_RUNTIME ~/ODIN_RUNTIME/dashboard_preview ~/ODIN_RUNTIME/logs ~/ODIN_RUNTIME/logs/system
mount | grep -E "/home|ODIN|vdo" || true
df -h ~/ODIN_RUNTIME
touch ~/ODIN_RUNTIME/.write_test && rm ~/ODIN_RUNTIME/.write_test
touch ~/ODIN_RUNTIME/dashboard_preview/.write_test && rm ~/ODIN_RUNTIME/dashboard_preview/.write_test
touch ~/ODIN_RUNTIME/logs/system/.write_test && rm ~/ODIN_RUNTIME/logs/system/.write_test
```

Se algum `touch` falhar no host real:

```bash
sudo chown -R "$USER":"$USER" ~/ODIN_RUNTIME
sudo chmod -R u+rwX ~/ODIN_RUNTIME
sudo find ~/ODIN_RUNTIME -type d -exec chmod 775 {} \;
sudo find ~/ODIN_RUNTIME -type f -exec chmod 664 {} \;
```

Se a filesystem estiver montada read-only:

```bash
mount | grep " / "
sudo dmesg | tail -n 100
sudo mount -o remount,rw /
```

### 14.6 Comandos recomendados para repetir RC1.9-FINAL no host real

```bash
cd ~/ODIN_RUNTIME/app
grep -E "ENABLE_REAL_TRADING|MT5_ORDER_SEND_ENABLED|BROKER_ALLOW_REAL_EXECUTION" ~/ODIN_RUNTIME/.env
sudo systemctl daemon-reload
sudo systemctl enable odin-runtime.service odin-dashboard.service
sudo systemctl start odin-runtime.service odin-dashboard.service
sudo systemctl status odin-runtime.service odin-dashboard.service --no-pager
sudo journalctl -u odin-runtime.service -u odin-dashboard.service -n 100 --no-pager
sudo reboot
# após reboot
sudo systemctl status odin-runtime.service odin-dashboard.service --no-pager
sudo journalctl -u odin-runtime.service -u odin-dashboard.service -b -n 200 --no-pager
cd ~/ODIN_RUNTIME/app
./run_odin.sh --dashboard-qa
./run_odin.sh --tui-once
./run_odin.sh --runtime-validate
```

## 15) Próxima ação formal — RC1.9-RETRY (host real)

Próxima ação obrigatória: executar `RC1.9-RETRY` em host real com `systemd` ativo, `sudo` funcional e reboot real observável.

Distinção técnica mantida:

- Falha atual é do ambiente de execução desta sessão (sandbox Codex sem sudo/DBus e runtime montado read-only nesta sessão).
- Esta evidência **não comprova falha funcional definitiva do ODIN no host real**.

### 15.1 Critérios PASS para RC1.9-RETRY

1. `odin-runtime.service` ativo após reboot.
2. `odin-dashboard.service` ativo após reboot.
3. `dashboard-qa` com `PASS`.
4. `tui-once` coerente com `SAFE_TO_TRADE=False` antes de validação completa.
5. `runtime-validate` com `PASS`.
6. Trading real permanece desativado (`ENABLE_REAL_TRADING=false`, `MT5_ORDER_SEND_ENABLED=false`, `BROKER_ALLOW_REAL_EXECUTION=false`).
7. Healthcheck/reconciliação executados ou bloqueados com motivo explícito.
8. Logs acessíveis via `journalctl`.
9. Sem falha silenciosa.

### 15.2 Critérios FAIL para RC1.9-RETRY

1. Qualquer serviço não arranca/recupera após reboot.
2. `dashboard-qa` falha.
3. `runtime-validate` falha.
4. Logs não acessíveis via `journalctl`.
5. Trading real permitido antes da validação completa.
6. Erro crítico sem motivo explícito.

## 16) Dashboard Operational Usability Review

O dashboard é avaliado aqui como componente operacional, não apenas como endpoint web.

### 16.1 Clareza dos estados principais

Estado atual da evidência (dashboard QA anterior + TUI/estado):

- Runtime state: **visível** (`RUNTIME STATE` / `Runtime`).
- System health: **visível** (`HEALTH STATE` / `Health`).
- Safe to trade: **visível** (`SAFE_TO_TRADE False`).
- Trading real bloqueado/permitido: **visível e explícito** (`TRADING REAL: BLOCKED`, `MT5 ORDER_SEND: BLOCKED`, `BROKER REAL: BLOCKED`).
- Estado MT5: **visível** (`MT5 status`, incluindo indisponibilidade).
- Estado ATLAS: **visível** (`ATLAS: SHADOW_ONLY`).
- Estado LLM/Ollama: **visível** (`LLM status`, provider e warnings).
- Últimos logs/eventos: **visível** (`EVENTS`, secção logs).
- Motivo de bloqueio: **parcialmente visível** (há bloqueios e sinais de `healthcheck_blocked`/`invalid_state_for_sync`, mas pode ser mais direto num painel dedicado).

### 16.2 Segurança operacional

Confirmações:

- O modo seguro está evidente.
- O bloqueio de trading real está evidente.
- O dashboard não expõe ação real antes de validação completa.
- MT5 indisponível/reconciliação bloqueada aparece com razão explícita quando consultado (`invalid_state_for_sync`, indisponibilidade da biblioteca MT5).

Risco residual de usabilidade:

- A razão dominante de bloqueio poderia estar mais destacada numa área única e persistente.

### 16.3 Intuitividade para operador

Avaliação operacional:

- Operador consegue perceber rapidamente se o sistema está bloqueado e sem permissão de trading real.
- Operador consegue identificar sinais de falha de MT5 e de runtime.
- Ainda falta orientação mais explícita de “próxima ação recomendada” para reduzir ambiguidade operacional em incidentes.

### 16.4 Diagnóstico de falhas

Capacidade atual de resposta rápida:

- “ODIN está ligado?”: parcialmente (via páginas e estado runtime).
- “Runtime está vivo?”: sim (estado/runtime/eventos/heartbeat quando disponível).
- “Dashboard está atualizado?”: sim, via rotas e conteúdo dinâmico.
- “MT5 está ligado?”: sim, com status explícito.
- “Reconciliação passou/falhou?”: há evidência, mas poderia ter resumo dedicado de última reconciliação.
- “Trading real está bloqueado?”: sim, de forma explícita.
- “Qual razão do bloqueio?”: existe, mas não centralizada num painel único.
- “Erro recente nos logs?”: sim, via secção de eventos/logs.
- “Falha silenciosa?”: não houve evidência de maquilhagem; quando falha, falha explicitamente.

### 16.5 Pontos de melhoria (não implementar nesta fase)

1. Painel “Estado Geral” sempre visível com semáforo operacional.
2. Indicador visual forte e persistente para `SAFE_TO_TRADE`.
3. Secção dedicada “Motivo atual de bloqueio”.
4. Secção “Última validação” (`runtime-validate`) com timestamp/resultado.
5. Secção “Última reconciliação MT5” com estado e motivo.
6. Secção “Ação recomendada agora” orientada ao operador.
7. Logs com filtro por severidade/módulo.
8. Atalho para healthcheck operacional.
9. Atalho para exportar diagnóstico operacional.
10. Separação visual clara entre modo observação e modo controlo.

### 16.6 Critério mínimo para aceitar o dashboard nesta fase

O dashboard só é aceitável se:

1. Mostrar claramente trading real bloqueado.
2. Não esconder falhas.
3. Não apresentar estados ambíguos.
4. Permitir perceber motivo de bloqueio.
5. Permitir distinguir erro de sistema, MT5, LLM e configuração.
6. Responder HTTP 200 nas rotas principais.
7. Não depender de dados falsos para parecer saudável.

Avaliação para RC1.9 atual:

- Critério operacional de clareza/segurança: **parcialmente atendido** com boa base, pendente de refinamentos de usabilidade.
- Estado global RC1.9: mantém-se **FAIL** por bloqueadores de ambiente (systemd/reboot/write access), não por relaxamento de segurança no dashboard.

### 16.7 Nota de governança operacional

O dashboard é considerado componente operacional crítico do ODIN. A validação futura não deve limitar-se a HTTP 200; deve incluir avaliação de clareza, segurança, diagnóstico e usabilidade para operador.
