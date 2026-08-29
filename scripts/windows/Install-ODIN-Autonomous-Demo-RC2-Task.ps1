[CmdletBinding()]
param(
    [string]$TaskName = "ODIN Autonomous Demo Operations RC2",
    [string]$RepoRoot = "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin",
    [string]$WorkingDirectory = "D:\ODIN_LOCAL"
)

$ErrorActionPreference = "Stop"
$launcher = Join-Path $RepoRoot "scripts\windows\Start-ODIN-Autonomous-Demo-RC2.ps1"
$dashboardLauncher = Join-Path $RepoRoot "scripts\windows\Start-ODIN-Dashboard-Persistent.ps1"
$resourceProbe = Join-Path $RepoRoot "scripts\windows\Get-ODIN-Autonomous-Demo-Resources.ps1"
$taskWrapper = Join-Path $RepoRoot "scripts\windows\Start-ODIN-Autonomous-Demo-RC2.cmd"
$venvPython = Join-Path $WorkingDirectory "runtime\mt5_probe_venv\Scripts\python.exe"
$venvConfiguration = Join-Path $WorkingDirectory "runtime\mt5_probe_venv\pyvenv.cfg"
foreach ($requiredSource in @($launcher, $dashboardLauncher, $resourceProbe, $taskWrapper)) {
    if (-not (Test-Path -LiteralPath $requiredSource)) {
        throw "ODIN RC2 launcher unavailable."
    }
}
if (-not (Test-Path -LiteralPath $WorkingDirectory -PathType Container)) {
    throw "ODIN RC2 local working directory unavailable."
}
if (-not (Test-Path -LiteralPath $venvPython) -or -not (Test-Path -LiteralPath $venvConfiguration)) {
    throw "ODIN RC2 Python runtime is unavailable."
}
$basePythonLine = Get-Content -LiteralPath $venvConfiguration |
    Where-Object { $_ -match '^executable\s*=\s*' } | Select-Object -First 1
$basePython = ($basePythonLine -replace '^executable\s*=\s*', '').Trim()
if (-not (Test-Path -LiteralPath $basePython -PathType Leaf)) {
    throw "ODIN RC2 base Python runtime is unavailable."
}
$runtimeRoot = Join-Path $WorkingDirectory "runtime"
$installedLauncher = Join-Path $runtimeRoot "Start-ODIN-Autonomous-Demo-RC2.ps1"
$installedDashboardLauncher = Join-Path $runtimeRoot "Start-ODIN-Dashboard-Persistent.ps1"
$installedResourceProbe = Join-Path $runtimeRoot "Get-ODIN-Autonomous-Demo-Resources.ps1"
$installedTaskWrapper = Join-Path $runtimeRoot "Start-ODIN-Autonomous-Demo-RC2.cmd"
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
Copy-Item -LiteralPath $launcher -Destination $installedLauncher -Force
Copy-Item -LiteralPath $dashboardLauncher -Destination $installedDashboardLauncher -Force
Copy-Item -LiteralPath $resourceProbe -Destination $installedResourceProbe -Force
$normalizedWrapper = ([IO.File]::ReadAllText($taskWrapper) -replace "`r?`n", "`r`n")
$wrapperBytes = [Text.Encoding]::ASCII.GetBytes($normalizedWrapper)
[IO.File]::WriteAllBytes($installedTaskWrapper, $wrapperBytes)
$sourceHash = (Get-FileHash -LiteralPath $launcher -Algorithm SHA256).Hash
$installedHash = (Get-FileHash -LiteralPath $installedLauncher -Algorithm SHA256).Hash
$dashboardSourceHash = (Get-FileHash -LiteralPath $dashboardLauncher -Algorithm SHA256).Hash
$dashboardInstalledHash = (Get-FileHash -LiteralPath $installedDashboardLauncher -Algorithm SHA256).Hash
$resourceProbeSourceHash = (Get-FileHash -LiteralPath $resourceProbe -Algorithm SHA256).Hash
$resourceProbeInstalledHash = (Get-FileHash -LiteralPath $installedResourceProbe -Algorithm SHA256).Hash
$sha256 = [Security.Cryptography.SHA256]::Create()
$wrapperSourceHash = ([BitConverter]::ToString($sha256.ComputeHash($wrapperBytes))).Replace('-', '')
$sha256.Dispose()
$wrapperInstalledHash = (Get-FileHash -LiteralPath $installedTaskWrapper -Algorithm SHA256).Hash
if (
    $sourceHash -ne $installedHash -or
    $dashboardSourceHash -ne $dashboardInstalledHash -or
    $resourceProbeSourceHash -ne $resourceProbeInstalledHash -or
    $wrapperSourceHash -ne $wrapperInstalledHash
) {
    throw "ODIN RC2 installed launcher hash mismatch."
}

$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$arguments = "/d /c call `"$installedTaskWrapper`""
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\cmd.exe" -Argument $arguments -WorkingDirectory $WorkingDirectory
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
Write-Output "PYTHON_RUNTIME=$basePython"
Write-Output "TASK_WRAPPER=$installedTaskWrapper"
Write-Output "INSTALLED_LAUNCHER=$installedLauncher"
Write-Output "LAUNCHER_SHA256=$installedHash"
Write-Output "DASHBOARD_LAUNCHER_SHA256=$dashboardInstalledHash"
Write-Output "RESOURCE_PROBE_SHA256=$resourceProbeInstalledHash"
Write-Output "TASK_WRAPPER_SHA256=$wrapperInstalledHash"
