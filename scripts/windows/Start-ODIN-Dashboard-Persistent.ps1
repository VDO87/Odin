[CmdletBinding()]
param(
    [string]$RepoRoot = "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin",
    [string]$LogRoot = "D:\ODIN_LOCAL\logs\autonomous-demo"
)

$ErrorActionPreference = "Stop"
$Url = "http://127.0.0.1:8765/health"

function Test-OdinDashboard {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

if (Test-OdinDashboard) {
    exit 0
}

New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$stdout = Join-Path $LogRoot "dashboard.stdout.log"
$stderr = Join-Path $LogRoot "dashboard.stderr.log"
$command = "cd /home/odin/projects/odin && ulimit -n 8192 2>/dev/null || true; exec python3 -m odin.cli dashboard --host 127.0.0.1 --port 8765"
Start-Process -FilePath "wsl.exe" `
    -ArgumentList @("-d", "Ubuntu-ODIN", "--user", "odin", "--exec", "sh", "-lc", $command) `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr | Out-Null

for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Seconds 1
    if (Test-OdinDashboard) {
        exit 0
    }
}

throw "ODIN dashboard did not recover within the bounded startup window."
