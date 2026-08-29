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
$bootstrap = Join-Path $RepoRoot "scripts\windows\mt5_autonomous_demo_bootstrap.py"
$venvPython = Join-Path $WorkingDirectory "runtime\mt5_probe_venv\Scripts\python.exe"
$venvConfiguration = Join-Path $WorkingDirectory "runtime\mt5_probe_venv\pyvenv.cfg"
foreach ($requiredSource in @($launcher, $dashboardLauncher, $resourceProbe, $taskWrapper, $bootstrap)) {
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

$gitStatus = @(& wsl.exe -d Ubuntu-ODIN --user odin --exec git -C /home/odin/projects/odin status --porcelain)
if ($LASTEXITCODE -ne 0 -or $gitStatus.Count -ne 0) {
    throw "ODIN RC2 runtime installation requires a clean Git checkpoint."
}
$checkpoint = (& wsl.exe -d Ubuntu-ODIN --user odin --exec git -C /home/odin/projects/odin rev-parse --short=12 HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $checkpoint -notmatch '^[0-9a-f]{7,12}$') {
    throw "ODIN RC2 checkpoint lookup failed."
}
$installedCodeRoot = Join-Path $runtimeRoot ("autonomous-demo\{0}" -f $checkpoint)
$sourceTrees = @(
    [pscustomobject]@{ Source = (Join-Path $RepoRoot "src\odin"); Relative = "src\odin" },
    [pscustomobject]@{ Source = (Join-Path $RepoRoot "scripts\windows"); Relative = "scripts\windows" }
)
foreach ($tree in $sourceTrees) {
    if (-not (Test-Path -LiteralPath $tree.Source -PathType Container)) {
        throw "ODIN RC2 versioned runtime source unavailable."
    }
}

function Get-CodeEntries([string]$Root, [object[]]$Trees) {
    $entries = @()
    foreach ($tree in $Trees) {
        Get-ChildItem -LiteralPath $tree.Source -Recurse -File | Where-Object {
            $_.Extension -ne '.pyc' -and $_.FullName -notmatch '\\(__pycache__|\.pytest_cache)\\'
        } | ForEach-Object {
            $suffix = $_.FullName.Substring($tree.Source.Length).TrimStart('\')
            $relative = Join-Path $tree.Relative $suffix
            $entries += [pscustomobject]@{
                Relative = $relative
                Hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            }
        }
    }
    return @($entries | Sort-Object Relative)
}

$sourceEntries = Get-CodeEntries -Root $RepoRoot -Trees $sourceTrees
if (-not (Test-Path -LiteralPath $installedCodeRoot)) {
    foreach ($entry in $sourceEntries) {
        $sourcePath = Join-Path $RepoRoot $entry.Relative
        $destination = Join-Path $installedCodeRoot $entry.Relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
        Copy-Item -LiteralPath $sourcePath -Destination $destination
    }
}
$installedEntries = @(
    Get-ChildItem -LiteralPath $installedCodeRoot -Recurse -File | Where-Object {
        $_.Extension -ne '.pyc' -and $_.FullName -notmatch '\\(__pycache__|\.pytest_cache)\\' -and
        $_.Name -ne 'runtime-manifest.json'
    } | ForEach-Object {
        [pscustomobject]@{
            Relative = $_.FullName.Substring($installedCodeRoot.Length).TrimStart('\')
            Hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        }
    } | Sort-Object Relative
)
$sourceInventory = $sourceEntries | ConvertTo-Json -Compress
$installedInventory = $installedEntries | ConvertTo-Json -Compress
if ($sourceInventory -ne $installedInventory) {
    throw "ODIN RC2 versioned runtime hash mismatch."
}
$inventoryBytes = [Text.Encoding]::UTF8.GetBytes($installedInventory)
$inventoryHasher = [Security.Cryptography.SHA256]::Create()
$inventoryHash = ([BitConverter]::ToString($inventoryHasher.ComputeHash($inventoryBytes))).Replace('-', '')
$inventoryHasher.Dispose()
$runtimeManifest = [ordered]@{
    schema = 'odin.autonomous_demo_runtime/v1'
    checkpoint = $checkpoint
    canonical_repo_root = $RepoRoot
    installed_code_root = $installedCodeRoot
    code_files = $installedEntries.Count
    code_inventory_sha256 = $inventoryHash
    contains_environment_file = $false
    safe_to_trade = $false
    real_trading = $false
    execution_allowed = $false
}
$runtimeManifestPath = Join-Path $installedCodeRoot 'runtime-manifest.json'
[IO.File]::WriteAllText(
    $runtimeManifestPath,
    ($runtimeManifest | ConvertTo-Json),
    [Text.UTF8Encoding]::new($false)
)

$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$installedBootstrap = Join-Path $installedCodeRoot "scripts\windows\mt5_autonomous_demo_bootstrap.py"
$arguments = "`"$installedBootstrap`" --runtime-root `"$installedCodeRoot`" --canonical-repo-root `"$RepoRoot`" --persistent-task"
$action = New-ScheduledTaskAction -Execute $basePython -Argument $arguments -WorkingDirectory $WorkingDirectory
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
Write-Output "RUNTIME_CHECKPOINT=$checkpoint"
Write-Output "INSTALLED_CODE_ROOT=$installedCodeRoot"
Write-Output "CODE_INVENTORY_SHA256=$inventoryHash"
Write-Output "RUNTIME_MANIFEST=$runtimeManifestPath"
Write-Output "INSTALLED_LAUNCHER=$installedLauncher"
Write-Output "LAUNCHER_SHA256=$installedHash"
Write-Output "DASHBOARD_LAUNCHER_SHA256=$dashboardInstalledHash"
Write-Output "RESOURCE_PROBE_SHA256=$resourceProbeInstalledHash"
Write-Output "TASK_WRAPPER_SHA256=$wrapperInstalledHash"
