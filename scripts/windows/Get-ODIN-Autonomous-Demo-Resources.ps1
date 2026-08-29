[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [int]$SupervisorProcessId,
    [string]$Root = "D:\ODIN_LOCAL"
)

$ErrorActionPreference = "Stop"
$gpuName = $null
$gpuTemperature = $null
$gpuUtilization = $null
$gpuMemoryTotal = $null
$gpuMemoryUsed = $null
$gpuCommand = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
if ($null -ne $gpuCommand) {
    $gpu = & $gpuCommand.Source `
        --query-gpu=name,temperature.gpu,utilization.gpu,memory.total,memory.used `
        --format=csv,noheader,nounits 2>$null | Select-Object -First 1
    if ($LASTEXITCODE -eq 0 -and $gpu) {
        $parts = @($gpu.Split(',') | ForEach-Object { $_.Trim() })
        if ($parts.Count -eq 5) {
            $gpuName = $parts[0]
            $gpuTemperature = [double]$parts[1]
            $gpuUtilization = [double]$parts[2]
            $gpuMemoryTotal = [double]$parts[3]
            $gpuMemoryUsed = [double]$parts[4]
        }
    }
}

$cpuTemperatures = @(
    Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature `
        -ErrorAction SilentlyContinue |
        ForEach-Object { [math]::Round(($_.CurrentTemperature / 10) - 273.15, 1) }
)
$cpuLoad = (Get-CimInstance Win32_Processor |
    Measure-Object -Property LoadPercentage -Average).Average
$computer = Get-CimInstance Win32_ComputerSystem
$operatingSystem = Get-CimInstance Win32_OperatingSystem
$disk = Get-PSDrive -Name D
$supervisor = Get-Process -Id $SupervisorProcessId -ErrorAction Stop

$matchingSupervisors = @(
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -eq 'python.exe' -and
            $_.CommandLine -match 'mt5_autonomous_demo_supervisor\.py'
        }
)
$supervisorIds = @{}
$matchingSupervisors | ForEach-Object { $supervisorIds[[int]$_.ProcessId] = $true }
$logicalSupervisors = @(
    $matchingSupervisors |
        Where-Object { -not $supervisorIds.ContainsKey([int]$_.ParentProcessId) }
)

$runningWsl = @(
    & wsl.exe --list --running --quiet 2>$null |
        ForEach-Object { ([string]$_).Replace([string][char]0, '').Trim() } |
        Where-Object { $_ }
)
$wslRunning = $runningWsl -contains 'Ubuntu-ODIN'
$wslFdSoftLimit = $null
$wslProcessCount = $null
$wslMemoryTotal = $null
$wslMemoryAvailable = $null
if ($wslRunning) {
    $fdValue = & wsl.exe -d Ubuntu-ODIN --user odin --exec sh -lc 'ulimit -n' 2>$null
    if ($LASTEXITCODE -eq 0 -and "$fdValue" -match '^\d+$') {
        $wslFdSoftLimit = [int]$fdValue
    }
    $wslProcesses = @(& wsl.exe -d Ubuntu-ODIN --user odin --exec ps -e --no-headers 2>$null)
    if ($LASTEXITCODE -eq 0) {
        $wslProcessCount = $wslProcesses.Count
    }
    $wslMemory = @(& wsl.exe -d Ubuntu-ODIN --user odin --exec free -b 2>$null)
    $memoryLine = $wslMemory | Where-Object { $_ -match '^Mem:\s+' } | Select-Object -First 1
    if ($memoryLine -and $memoryLine -match '^Mem:\s+(\d+)\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)') {
        $wslMemoryTotal = [math]::Round([double]$Matches[1] / 1MB, 0)
        $wslMemoryAvailable = [math]::Round([double]$Matches[2] / 1MB, 0)
    }
}

$logBytes = @(
    Get-ChildItem -LiteralPath (Join-Path $Root 'logs') -File -Recurse -ErrorAction SilentlyContinue
    Get-ChildItem -LiteralPath (Join-Path $Root 'reports') -File -Recurse -ErrorAction SilentlyContinue
) | Measure-Object -Property Length -Sum
$sqliteBytes = Get-ChildItem -LiteralPath (Join-Path $Root 'runtime') -File `
    -Filter '*.sqlite*' -ErrorAction SilentlyContinue |
    Measure-Object -Property Length -Sum
$ollamaRunning = @(Get-Process -Name 'ollama', 'ollama app' -ErrorAction SilentlyContinue).Count -gt 0
$hermesRunning = @(
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -match 'hermes_cli\.main serve' }
).Count -gt 0

[ordered]@{
    schema = 'odin.autonomous_demo_resource_snapshot/v1'
    probe_status = 'OK'
    sampled_at_utc = [DateTime]::UtcNow.ToString('o')
    cpu_load_percent = [double]$cpuLoad
    cpu_temperatures_c = $cpuTemperatures
    memory_total_mb = [math]::Round([double]$computer.TotalPhysicalMemory / 1MB, 0)
    memory_available_mb = [math]::Round([double]$operatingSystem.FreePhysicalMemory / 1KB, 0)
    gpu_name = $gpuName
    gpu_temperature_c = $gpuTemperature
    gpu_utilization_percent = $gpuUtilization
    gpu_memory_total_mb = $gpuMemoryTotal
    gpu_memory_used_mb = $gpuMemoryUsed
    disk_total_gb = [math]::Round(([double]$disk.Used + [double]$disk.Free) / 1GB, 2)
    disk_free_gb = [math]::Round([double]$disk.Free / 1GB, 2)
    process_handles = [int]$supervisor.HandleCount
    supervisor_processes = $matchingSupervisors.Count
    supervisor_logical_instances = $logicalSupervisors.Count
    wsl_running = $wslRunning
    wsl_process_count = $wslProcessCount
    wsl_fd_soft_limit = $wslFdSoftLimit
    wsl_memory_total_mb = $wslMemoryTotal
    wsl_memory_available_mb = $wslMemoryAvailable
    logs_and_reports_bytes = [double]$logBytes.Sum
    sqlite_bytes = [double]$sqliteBytes.Sum
    ollama_running = $ollamaRunning
    hermes_running = $hermesRunning
} | ConvertTo-Json -Compress -Depth 4
