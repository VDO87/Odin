$ErrorActionPreference = "Stop"
$launcher = "D:\ODIN_LOCAL\cockpit\Start-ODIN-Cockpit.ps1"
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "Launcher not found: $launcher"
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
Write-Output $shortcutPath
