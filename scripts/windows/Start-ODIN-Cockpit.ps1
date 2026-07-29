[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [ValidateRange(60, 43200)]
    [int]$WatchdogSeconds = 21600
)

$ErrorActionPreference = "Stop"
$Distro = "Ubuntu-ODIN"
$Port = 8765
$Url = "http://127.0.0.1:$Port/"
$StateRoot = "D:\ODIN_LOCAL\cockpit"
$LogRoot = Join-Path $StateRoot "logs"
$Stdout = Join-Path $LogRoot "dashboard.stdout.log"
$Stderr = Join-Path $LogRoot "dashboard.stderr.log"

function Test-OdinCockpit {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -eq 200 -and $response.Content -match "ODIN Cockpit"
    }
    catch {
        return $false
    }
}

New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
if (-not (Test-OdinCockpit)) {
    $arguments = "-d $Distro -u odin --exec /home/odin/projects/odin/scripts/run_dashboard_local.sh $WatchdogSeconds"
    $process = Start-Process -FilePath "wsl.exe" -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr
    $ready = $false
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        Start-Sleep -Seconds 1
        if (Test-OdinCockpit) {
            $ready = $true
            break
        }
    }
    if (-not $ready) {
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
        }
        throw "ODIN cockpit did not pass the localhost smoke. Review $Stderr"
    }
}

if (-not $NoBrowser) {
    Start-Process $Url
}

Write-Output "ODIN cockpit ready at $Url (local-only, read-only)."
