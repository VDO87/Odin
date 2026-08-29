$ErrorActionPreference = "Stop"
$launcher = "D:\ODIN_LOCAL\cockpit\Start-ODIN-Cockpit.ps1"
$refresh = "D:\ODIN_LOCAL\cockpit\Refresh-ODIN-Observations.ps1"
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "Launcher not found: $launcher"
}
if (-not (Test-Path -LiteralPath $refresh)) {
    throw "Observation refresh script not found: $refresh"
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "ODIN TradeDesk (Demo).lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$launcher`""
$shortcut.WorkingDirectory = "D:\ODIN_LOCAL\cockpit"
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
$shortcut.Description = "Open the ODIN local TradeDesk DEMO replay"
$shortcut.Save()

$refreshShortcutPath = Join-Path $desktop "ODIN Refresh DEMO Observations.lnk"
$refreshShortcut = $shell.CreateShortcut($refreshShortcutPath)
$refreshShortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$refreshShortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$refresh`""
$refreshShortcut.WorkingDirectory = "D:\ODIN_LOCAL\cockpit"
$refreshShortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,238"
$refreshShortcut.Description = "Validate persistent OANDA DEMO state and refresh public observations; no execution"
$refreshShortcut.Save()

Write-Output $shortcutPath
Write-Output $refreshShortcutPath
