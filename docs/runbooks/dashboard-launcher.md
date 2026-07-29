# Launcher do cockpit ODIN

## Limite de segurança

O cockpit é local e apenas observacional. O launcher liga exclusivamente a
`127.0.0.1:8765`, mantém `safe_to_trade=false`, `real_trading=false` e
`execution_allowed=false`, e não aceita credenciais nem executa fluxos MT5.

O processo Linux recebe `ulimit -n 8192` e um watchdog externo `timeout`; por
defeito termina ao fim de seis horas. O launcher não cria um daemon permanente.

## Instalação Windows

Os ficheiros fonte estão em `scripts/windows/`. Copie ambos para
`D:\ODIN_LOCAL\cockpit\` e execute apenas no processo:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\ODIN_LOCAL\cockpit\install_cockpit_shortcut.ps1
```

Isto cria `ODIN Cockpit (Local).lnk` no Ambiente de Trabalho, com ícone do
Windows. O atalho abre o browser padrão só depois de o cockpit responder no
localhost. Logs do processo ficam em `D:\ODIN_LOCAL\cockpit\logs\`.

## Verificação e paragem

O launcher confirma a página inicial e não abre uma segunda instância se a
porta local já responder. Para teste sem browser use:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\ODIN_LOCAL\cockpit\Start-ODIN-Cockpit.ps1 -NoBrowser -WatchdogSeconds 120
```

Em caso de falha, leia `dashboard.stderr.log`, mantenha a execução bloqueada e
faça o smoke local antes de tentar novamente.
