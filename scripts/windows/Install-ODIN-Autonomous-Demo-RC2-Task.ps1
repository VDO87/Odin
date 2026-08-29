[CmdletBinding()]
param(
    [string]$TaskName = "ODIN Autonomous Demo Operations RC2",
    [string]$RepoRoot = "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin",
    [string]$WorkingDirectory = "D:\ODIN_LOCAL"
)

$ErrorActionPreference = "Stop"
$launcher = Join-Path $RepoRoot "scripts\windows\Start-ODIN-Autonomous-Demo-RC2.ps1"
$dashboardLauncher = Join-Path $RepoRoot "scripts\windows\Start-ODIN-Dashboard-Persistent.ps1"
$taskWrapper = Join-Path $RepoRoot "scripts\windows\Start-ODIN-Autonomous-Demo-RC2.cmd"
foreach ($requiredSource in @($launcher, $dashboardLauncher, $taskWrapper)) {
    if (-not (Test-Path -LiteralPath $requiredSource)) {
        throw "ODIN RC2 launcher unavailable."
    }
}
if (-not (Test-Path -LiteralPath $WorkingDirectory -PathType Container)) {
    throw "ODIN RC2 local working directory unavailable."
}
$runtimeRoot = Join-Path $WorkingDirectory "runtime"
$installedLauncher = Join-Path $runtimeRoot "Start-ODIN-Autonomous-Demo-RC2.ps1"
$installedDashboardLauncher = Join-Path $runtimeRoot "Start-ODIN-Dashboard-Persistent.ps1"
$installedTaskWrapper = Join-Path $runtimeRoot "Start-ODIN-Autonomous-Demo-RC2.cmd"
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
Copy-Item -LiteralPath $launcher -Destination $installedLauncher -Force
Copy-Item -LiteralPath $dashboardLauncher -Destination $installedDashboardLauncher -Force
$normalizedWrapper = ([IO.File]::ReadAllText($taskWrapper) -replace "`r?`n", "`r`n")
$wrapperBytes = [Text.Encoding]::ASCII.GetBytes($normalizedWrapper)
[IO.File]::WriteAllBytes($installedTaskWrapper, $wrapperBytes)
$sourceHash = (Get-FileHash -LiteralPath $launcher -Algorithm SHA256).Hash
$installedHash = (Get-FileHash -LiteralPath $installedLauncher -Algorithm SHA256).Hash
$dashboardSourceHash = (Get-FileHash -LiteralPath $dashboardLauncher -Algorithm SHA256).Hash
$dashboardInstalledHash = (Get-FileHash -LiteralPath $installedDashboardLauncher -Algorithm SHA256).Hash
$sha256 = [Security.Cryptography.SHA256]::Create()
$wrapperSourceHash = ([BitConverter]::ToString($sha256.ComputeHash($wrapperBytes))).Replace('-', '')
$sha256.Dispose()
$wrapperInstalledHash = (Get-FileHash -LiteralPath $installedTaskWrapper -Algorithm SHA256).Hash
if (
    $sourceHash -ne $installedHash -or
    $dashboardSourceHash -ne $dashboardInstalledHash -or
    $wrapperSourceHash -ne $wrapperInstalledHash
) {
    throw "ODIN RC2 installed launcher hash mismatch."
}

$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$arguments = "/d /c call $installedTaskWrapper"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $arguments -WorkingDirectory $WorkingDirectory
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
Write-Output "WORKING_DIRECTORY=$WorkingDirectory"
Write-Output "INSTALLED_LAUNCHER=$installedLauncher"
Write-Output "LAUNCHER_SHA256=$installedHash"
Write-Output "DASHBOARD_LAUNCHER_SHA256=$dashboardInstalledHash"
Write-Output "TASK_WRAPPER_SHA256=$wrapperInstalledHash"
