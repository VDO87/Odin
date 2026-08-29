[CmdletBinding()]
param(
    [string]$TaskName = "ODIN Autonomous Demo Operations RC2",
    [string]$RepoRoot = "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin"
)

$ErrorActionPreference = "Stop"
$launcher = Join-Path $RepoRoot "scripts\windows\Start-ODIN-Autonomous-Demo-RC2.ps1"
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "ODIN RC2 launcher unavailable."
}

$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$launcher`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory $RepoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Persistent local ODIN RC2 supervisor; DEMO only, REAL hard-blocked." `
    -Force | Out-Null

$task = Get-ScheduledTask -TaskName $TaskName
if ($task.TaskName -ne $TaskName) {
    throw "ODIN RC2 task validation failed."
}

Write-Output "TASK_NAME=$($task.TaskName)"
Write-Output "TASK_STATE=$($task.State)"
Write-Output "RUN_LEVEL=Limited"
Write-Output "LOGON_TYPE=Interactive"
Write-Output "MULTIPLE_INSTANCES=IgnoreNew"
