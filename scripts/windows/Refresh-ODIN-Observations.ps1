[CmdletBinding()]
param(
    [ValidateRange(5, 30)]
    [int]$Mt5TimeoutSeconds = 10,
    [ValidateRange(5, 60)]
    [int]$PublicDataTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$Distro = "Ubuntu-ODIN"
$Collector = Join-Path $PSScriptRoot "Read-ODIN-MT5-Demo.ps1"

if (-not (Test-Path -LiteralPath $Collector)) {
    throw "The bounded MT5 DEMO collector is unavailable."
}

Write-Output "[1/3] Collecting MT5 DEMO observation (read-only)."
& $Collector -TimeoutSeconds $Mt5TimeoutSeconds
if ($LASTEXITCODE -ne 0) { throw "MT5 DEMO observation failed; no further collection was attempted." }

Write-Output "[2/3] Refreshing bounded public ECB observation."
& wsl.exe -d $Distro -u odin -- bash -lc "cd /home/odin/projects/odin && ulimit -n 8192 && timeout 45s python3 -m odin.cli public-data-refresh --timeout-seconds $PublicDataTimeoutSeconds"
if ($LASTEXITCODE -ne 0) { throw "Public observation refresh failed; execution remains blocked." }

Write-Output "[3/3] Writing local operational report."
& wsl.exe -d $Distro -u odin -- bash -lc "cd /home/odin/projects/odin && ulimit -n 8192 && timeout 45s python3 -m odin.cli operational-report"
if ($LASTEXITCODE -ne 0) { throw "Operational report failed; execution remains blocked." }

Write-Output "ODIN observations refreshed locally. No orders, strategies, or execution were run."
