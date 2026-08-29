@echo off
setlocal
if not exist "D:\ODIN_LOCAL\logs\autonomous-demo" mkdir "D:\ODIN_LOCAL\logs\autonomous-demo"
echo %DATE% %TIME% WRAPPER_STARTED>>"D:\ODIN_LOCAL\logs\autonomous-demo\task-wrapper.trace.log"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "D:\ODIN_LOCAL\runtime\Start-ODIN-Autonomous-Demo-RC2.ps1"
set "ODIN_RC2_EXIT=%ERRORLEVEL%"
echo %DATE% %TIME% WRAPPER_EXIT_%ODIN_RC2_EXIT%>>"D:\ODIN_LOCAL\logs\autonomous-demo\task-wrapper.trace.log"
exit /b %ODIN_RC2_EXIT%
