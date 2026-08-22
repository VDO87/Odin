[CmdletBinding()]
param(
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Root = Join-Path $Desktop "ODIN - CONTROL CENTER"
$Repo = "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin"
$Reports = "D:\ODIN_LOCAL\reports"
$Runtime = "D:\ODIN_LOCAL\runtime"
$PowerShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$Explorer = "$env:SystemRoot\explorer.exe"
$Wsl = "$env:SystemRoot\System32\wsl.exe"
$Shell32 = "$env:SystemRoot\System32\shell32.dll"
$StatusScript = Join-Path $Repo "scripts\windows\Refresh-ODIN-Control-Center-Status.ps1"
$DryRunScript = Join-Path $Repo "scripts\windows\Invoke-ODIN-MT5-Demo-DryRun.ps1"
$CockpitLauncher = "D:\ODIN_LOCAL\cockpit\Start-ODIN-Cockpit.ps1"
$TradeDeskUrl = "http://127.0.0.1:8765/"
$CockpitUrl = "http://127.0.0.1:8765/cockpit"

$Folders = @(
    "01 - OPERACAO",
    "02 - DEMO TRADING",
    "03 - SUPERVISAO",
    "04 - LOGS",
    "05 - DESENVOLVIMENTO",
    "06 - SISTEMA",
    "99 - EMERGENCIA"
)

function New-OdinShortcut {
    param(
        [Parameter(Mandatory)][string]$Folder,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Target,
        [string]$Arguments = "",
        [string]$WorkingDirectory = "",
        [string]$Description = "",
        [string]$IconLocation = "$Shell32,0"
    )
    if (-not (Test-Path -LiteralPath $Target)) { return }
    $folderPath = Join-Path $Root $Folder
    $shortcutPath = Join-Path $folderPath "$Name.lnk"
    $shortcut = $script:WshShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $Target
    $shortcut.Arguments = $Arguments
    if ($WorkingDirectory -and (Test-Path -LiteralPath $WorkingDirectory)) {
        $shortcut.WorkingDirectory = $WorkingDirectory
    }
    $shortcut.Description = $Description
    $shortcut.IconLocation = $IconLocation
    $shortcut.Save()
}

function New-ExplorerShortcut {
    param(
        [Parameter(Mandatory)][string]$Folder,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Path,
        [string]$Description = "",
        [switch]$SelectFile,
        [string]$IconLocation = "$Shell32,3"
    )
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $arguments = if ($SelectFile) { "/select,`"$Path`"" } else { "`"$Path`"" }
    New-OdinShortcut -Folder $Folder -Name $Name -Target $Explorer -Arguments $arguments -WorkingDirectory (Split-Path -Parent $Path) -Description $Description -IconLocation $IconLocation
}

function Find-Mt5Logs([string]$OriginPath) {
    $terminalRoot = Join-Path $env:APPDATA "MetaQuotes\Terminal"
    if (-not (Test-Path -LiteralPath $terminalRoot)) { return $null }
    foreach ($directory in Get-ChildItem -LiteralPath $terminalRoot -Directory -ErrorAction SilentlyContinue) {
        $origin = Join-Path $directory.FullName "origin.txt"
        $logs = Join-Path $directory.FullName "logs"
        if ((Test-Path -LiteralPath $origin) -and (Test-Path -LiteralPath $logs)) {
            $observedOrigin = (Get-Content -LiteralPath $origin -Raw).Trim()
            if ($observedOrigin -eq $OriginPath) { return $logs }
        }
    }
    return $null
}

function Test-ControlCenterShortcuts {
    $errors = New-Object System.Collections.Generic.List[string]
    $links = @(Get-ChildItem -LiteralPath $Root -Filter "*.lnk" -File -Recurse -ErrorAction SilentlyContinue)
    foreach ($link in $links) {
        $shortcut = $script:WshShell.CreateShortcut($link.FullName)
        if (-not (Test-Path -LiteralPath $shortcut.TargetPath)) {
            $errors.Add("Missing target: $($link.FullName) -> $($shortcut.TargetPath)")
            continue
        }
        if ($shortcut.WorkingDirectory -and -not (Test-Path -LiteralPath $shortcut.WorkingDirectory)) {
            $errors.Add("Missing working directory: $($link.FullName) -> $($shortcut.WorkingDirectory)")
            continue
        }
        $commandSurface = "$($shortcut.TargetPath) $($shortcut.Arguments)"
        if ($commandSurface -match '(?i)order_send|canary_authorized\s*=\s*true') {
            $errors.Add("Forbidden execution surface: $($link.FullName)")
            continue
        }
        Write-Output "[OK] $($link.FullName)"
    }
    if ($links.Count -eq 0) { $errors.Add("No shortcuts found below $Root") }
    if ($errors.Count -gt 0) { throw ($errors -join [Environment]::NewLine) }
    Write-Output "Validated $($links.Count) shortcuts without launching trading or CANARY actions."
}

if (-not $ValidateOnly) {
    New-Item -ItemType Directory -Force -Path $Root | Out-Null
    foreach ($folder in $Folders) { New-Item -ItemType Directory -Force -Path (Join-Path $Root $folder) | Out-Null }
}
elseif (-not (Test-Path -LiteralPath $Root)) {
    throw "ODIN Control Center is not installed: $Root"
}

$script:WshShell = New-Object -ComObject WScript.Shell

if (-not $ValidateOnly) {
    $operation = "01 - OPERACAO"
    New-OdinShortcut -Folder $operation -Name "ODIN TradeDesk" -Target $PowerShell -Arguments "-NoProfile -ExecutionPolicy Bypass -Command `"& '$CockpitLauncher' -NoBrowser; Start-Process '$TradeDeskUrl'`"" -WorkingDirectory "D:\ODIN_LOCAL\cockpit" -Description "Inicia o dashboard local e abre o ODIN TradeDesk; execução financeira permanece bloqueada." -IconLocation "$Shell32,13"
    New-OdinShortcut -Folder $operation -Name "ODIN Technical Cockpit" -Target $PowerShell -Arguments "-NoProfile -ExecutionPolicy Bypass -Command `"& '$CockpitLauncher' -NoBrowser; Start-Process '$CockpitUrl'`"" -WorkingDirectory "D:\ODIN_LOCAL\cockpit" -Description "Inicia o dashboard local e abre o cockpit técnico read-only." -IconLocation "$Shell32,13"
    New-OdinShortcut -Folder $operation -Name "MetaTrader 5 - OANDA DEMO" -Target "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe" -WorkingDirectory "C:\Program Files\OANDA TMS MT5 Terminal" -Description "Abre exclusivamente a instalação OANDA TMS MT5 identificada. Não autoriza ordens." -IconLocation "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe,0"
    New-OdinShortcut -Folder $operation -Name "Hermes" -Target "C:\Users\ODIN\AppData\Local\hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe" -WorkingDirectory "C:\Users\ODIN\AppData\Local\hermes\hermes-agent\apps\desktop\release\win-unpacked" -Description "Abre o Hermes local; sem autoridade financeira." -IconLocation "C:\Users\ODIN\AppData\Local\hermes\hermes-agent\apps\desktop\release\win-unpacked\resources\icon.ico,0"
    New-OdinShortcut -Folder $operation -Name "ODIN Health Check" -Target $PowerShell -Arguments "-NoProfile -NoExit -ExecutionPolicy Bypass -File `"$StatusScript`" -HealthOnly" -WorkingDirectory $Reports -Description "Verificação local e read-only de endpoints, processos e guardrails." -IconLocation "$Shell32,167"

    $demo = "02 - DEMO TRADING"
    New-OdinShortcut -Folder $demo -Name "Stage 0 DEMO Dry Run" -Target $PowerShell -Arguments "-NoProfile -ExecutionPolicy Bypass -File `"$DryRunScript`"" -WorkingDirectory $Reports -Description "Executa apenas o Stage 0 DEMO. Não autoriza CANARY e não chama mt5.order_send." -IconLocation "$Shell32,238"
    New-ExplorerShortcut -Folder $demo -Name "Canary Preflight" -Path (Join-Path $Repo "docs\ODIN_DEMO_CANARY_PREFLIGHT.md") -Description "Abre o pre-flight; confirmação humana continua obrigatória." -IconLocation "$Shell32,71"
    New-ExplorerShortcut -Folder $demo -Name "Demo Execution Reports" -Path (Join-Path $Reports "demo-execution") -Description "Relatórios reais do Stage 0/DEMO execution." -IconLocation "$Shell32,70"
    New-ExplorerShortcut -Folder $demo -Name "MT5 DEMO Reports" -Path $Runtime -Description "Evidência read-only e runtime MT5 local." -IconLocation "$Shell32,70"

    $supervision = "03 - SUPERVISAO"
    New-OdinShortcut -Folder $supervision -Name "Daily Supervisor" -Target $Wsl -Arguments "-d Ubuntu-ODIN -u odin --exec sh -lc `"cd /home/odin/projects/odin && python3 -m odin.cli daily-supervisor --output-dir /mnt/d/ODIN_LOCAL/reports`"" -WorkingDirectory $Reports -Description "Gera uma vez o relatório Daily Supervisor; não altera o sistema." -IconLocation "$Shell32,238"
    New-OdinShortcut -Folder $supervision -Name "Weekly Evolution Gate" -Target $Wsl -Arguments "-d Ubuntu-ODIN -u odin --exec sh -lc `"cd /home/odin/projects/odin && python3 -m odin.cli weekly-evolution-gate --reports-dir /mnt/d/ODIN_LOCAL/reports --output-dir /mnt/d/ODIN_LOCAL/reports`"" -WorkingDirectory $Reports -Description "Gera uma vez o Weekly Evolution Gate; apenas propõe para revisão humana." -IconLocation "$Shell32,238"
    New-ExplorerShortcut -Folder $supervision -Name "Reports" -Path $Reports -Description "Diretório canónico de relatórios locais." -IconLocation "$Shell32,70"
    $latestDaily = Get-ChildItem -LiteralPath $Reports -File -Filter "odin-daily-supervisor-*.md" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -ne $latestDaily) { New-ExplorerShortcut -Folder $supervision -Name "Latest Daily Supervisor" -Path $latestDaily.FullName -Description "Último relatório Daily Supervisor existente." }
    $latestWeekly = Get-ChildItem -LiteralPath $Reports -File -Filter "odin-weekly-evolution-*.md" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -ne $latestWeekly) { New-ExplorerShortcut -Folder $supervision -Name "Latest Weekly Evolution" -Path $latestWeekly.FullName -Description "Último relatório Weekly Evolution existente." }

    $logs = "04 - LOGS"
    New-ExplorerShortcut -Folder $logs -Name "ODIN Logs" -Path "D:\ODIN_LOCAL\logs" -Description "Logs locais canónicos do ODIN." -IconLocation "$Shell32,70"
    New-ExplorerShortcut -Folder $logs -Name "Cockpit Logs" -Path "D:\ODIN_LOCAL\cockpit\logs" -Description "stdout/stderr reais do dashboard local." -IconLocation "$Shell32,70"
    $oandaMt5Logs = Find-Mt5Logs "C:\Program Files\OANDA TMS MT5 Terminal"
    if ($oandaMt5Logs) { New-ExplorerShortcut -Folder $logs -Name "MT5 OANDA DEMO Logs" -Path $oandaMt5Logs -Description "Logs da instalação MT5 OANDA TMS identificada." -IconLocation "$Shell32,70" }
    $localMt5Logs = Find-Mt5Logs "D:\ODIN_LOCAL\mt5"
    if ($localMt5Logs) { New-ExplorerShortcut -Folder $logs -Name "MT5 Local Logs" -Path $localMt5Logs -Description "Logs da instalação MT5 local separada." -IconLocation "$Shell32,70" }
    New-ExplorerShortcut -Folder $logs -Name "Hermes Logs" -Path "C:\Users\ODIN\AppData\Local\hermes\logs" -Description "Logs reais da aplicação Hermes." -IconLocation "$Shell32,70"
    New-ExplorerShortcut -Folder $logs -Name "Hermes Errors" -Path "C:\Users\ODIN\AppData\Local\hermes\logs\errors.log" -SelectFile -Description "Seleciona o ficheiro de erros real do Hermes." -IconLocation "$Shell32,109"
    New-ExplorerShortcut -Folder $logs -Name "ODIN Audit Documentation" -Path (Join-Path $Repo "docs\audits") -Description "Diretório existente de auditorias ODIN." -IconLocation "$Shell32,71"
    New-ExplorerShortcut -Folder $logs -Name "Decision Ledger" -Path (Join-Path $Runtime "shadow_decision_ledger.jsonl") -SelectFile -Description "Seleciona o Decision Ledger local e real." -IconLocation "$Shell32,71"
    New-ExplorerShortcut -Folder $logs -Name "SQLite Diagnostics" -Path (Join-Path $Runtime "public_data.sqlite") -SelectFile -Description "Seleciona a base SQLite local; não a modifica." -IconLocation "$Shell32,71"

    $development = "05 - DESENVOLVIMENTO"
    New-OdinShortcut -Folder $development -Name "Abrir ODIN no VS Code" -Target "C:\Users\ODIN\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd" -Arguments "--folder-uri vscode-remote://wsl+Ubuntu-ODIN/home/odin/projects/odin" -WorkingDirectory $Repo -Description "Abre o repositório ODIN no VS Code via WSL." -IconLocation "C:\Users\ODIN\AppData\Local\Programs\Microsoft VS Code\Code.exe,0"
    New-OdinShortcut -Folder $development -Name "Abrir Ubuntu-ODIN" -Target $Wsl -Arguments "-d Ubuntu-ODIN -u odin --cd /home/odin/projects/odin" -WorkingDirectory $Repo -Description "Abre uma shell WSL no repositório ODIN." -IconLocation "$Shell32,153"
    New-ExplorerShortcut -Folder $development -Name "Abrir Repositorio ODIN" -Path $Repo -Description "Abre o repositório canónico via UNC." -IconLocation "$Shell32,3"
    New-ExplorerShortcut -Folder $development -Name "Abrir Docs" -Path (Join-Path $Repo "docs") -Description "Abre a documentação canónica ODIN." -IconLocation "$Shell32,71"
    New-OdinShortcut -Folder $development -Name "Git Status ODIN" -Target $PowerShell -Arguments "-NoProfile -NoExit -Command `"wsl.exe -d Ubuntu-ODIN -u odin --exec git -C /home/odin/projects/odin status --short --branch`"" -WorkingDirectory $Repo -Description "Mostra o estado Git sem alterar o repositório." -IconLocation "$Shell32,167"

    $system = "06 - SISTEMA"
    New-OdinShortcut -Folder $system -Name "Windows Task Scheduler" -Target "$env:SystemRoot\System32\taskschd.msc" -WorkingDirectory "$env:SystemRoot\System32" -Description "Abre o Task Scheduler; não altera tarefas automaticamente." -IconLocation "$Shell32,166"
    New-OdinShortcut -Folder $system -Name "NVIDIA GPU Monitor" -Target $PowerShell -Arguments "-NoProfile -NoExit -Command `"& '$env:SystemRoot\System32\nvidia-smi.exe' -l 2`"" -WorkingDirectory "$env:SystemRoot\System32" -Description "Monitorização NVIDIA local; feche a consola para terminar." -IconLocation "$Shell32,22"
    New-OdinShortcut -Folder $system -Name "ODIN Process Status" -Target $PowerShell -Arguments "-NoProfile -NoExit -ExecutionPolicy Bypass -File `"$StatusScript`" -HealthOnly" -WorkingDirectory $Reports -Description "Estado read-only dos processos e endpoints ODIN." -IconLocation "$Shell32,167"
    New-OdinShortcut -Folder $system -Name "Ollama Models" -Target $PowerShell -Arguments "-NoProfile -NoExit -Command `"& 'C:\Users\ODIN\AppData\Local\Programs\Ollama\ollama.exe' list`"" -WorkingDirectory "C:\Users\ODIN\AppData\Local\Programs\Ollama" -Description "Lista modelos do Ollama instalado; não instala nada." -IconLocation "$Shell32,167"
    New-OdinShortcut -Folder $system -Name "Task Manager" -Target "$env:SystemRoot\System32\Taskmgr.exe" -WorkingDirectory "$env:SystemRoot\System32" -Description "Abre o Gestor de Tarefas." -IconLocation "$Shell32,166"
    New-OdinShortcut -Folder $system -Name "Resource Monitor" -Target "$env:SystemRoot\System32\resmon.exe" -WorkingDirectory "$env:SystemRoot\System32" -Description "Abre o Monitor de Recursos." -IconLocation "$Shell32,166"

    $emergency = "99 - EMERGENCIA"
    New-ExplorerShortcut -Folder $emergency -Name "ODIN STOP - Safe Stop Documentation" -Path (Join-Path $Repo "docs\runbooks\emergency-stop.md") -Description "Documentação de paragem segura; nenhuma ação destrutiva de um clique." -IconLocation "$Shell32,109"
    New-OdinShortcut -Folder $emergency -Name "Kill Switch Status" -Target $PowerShell -Arguments "-NoProfile -NoExit -ExecutionPolicy Bypass -File `"$StatusScript`" -KillSwitchOnly" -WorkingDirectory $Reports -Description "Consulta read-only do kill switch e guardrails." -IconLocation "$Shell32,109"
    New-ExplorerShortcut -Folder $emergency -Name "Recovery Documentation" -Path (Join-Path $Repo "docs\SECRET_HANDLING_AND_RECOVERY.md") -Description "Abre a documentação canónica de recuperação." -IconLocation "$Shell32,71"
    New-ExplorerShortcut -Folder $emergency -Name "Checkpoints" -Path "D:\ODIN_LOCAL\checkpoints" -Description "Abre os checkpoints locais existentes; não restaura nem elimina nada." -IconLocation "$Shell32,71"

    New-OdinShortcut -Folder "." -Name "Refresh ODIN Status" -Target $PowerShell -Arguments "-NoProfile -NoExit -ExecutionPolicy Bypass -File `"$StatusScript`"" -WorkingDirectory $Root -Description "Atualiza apenas ODIN - ESTADO ATUAL.txt a partir de evidência local." -IconLocation "$Shell32,238"
    & $StatusScript
}

Test-ControlCenterShortcuts
