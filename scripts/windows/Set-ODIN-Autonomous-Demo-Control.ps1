[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('PAUSE', 'RESUME', 'SAFE_STOP')]
    [string]$Action,
    [switch]$ConfirmResume,
    [string]$ControlPath = "D:\ODIN_LOCAL\state\autonomous_demo_control.json"
)

$ErrorActionPreference = "Stop"
if ($Action -eq 'RESUME' -and -not $ConfirmResume) {
    throw "RESUME requires -ConfirmResume and full runtime gate revalidation."
}
$parent = Split-Path -Parent $ControlPath
New-Item -ItemType Directory -Force -Path $parent | Out-Null
$payload = [ordered]@{
    schema = "odin.autonomous_demo_control/v1"
    action = $Action
    request_id = [guid]::NewGuid().ToString()
    requested_at_utc = [DateTime]::UtcNow.ToString("o")
    resume_requires_full_gate_revalidation = ($Action -eq 'RESUME')
    safe_to_trade = $false
    real_trading = $false
    execution_allowed = $false
}
$temporary = "$ControlPath.tmp"
$payload | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding utf8
Move-Item -LiteralPath $temporary -Destination $ControlPath -Force
Write-Output "CONTROL=$Action"
Write-Output "execution_allowed=false"
