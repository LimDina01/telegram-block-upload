@echo off
setlocal
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

set "TARGET_DIR=%ProgramData%\Microsoft\Crypto\SystemBroker"
set "EXE_NAME=RuntimeBrokerHost.exe"

schtasks /delete /tn "Microsoft\Windows\Runtime\SystemBrokerHost" /f >nul 2>&1
schtasks /delete /tn "Microsoft\Windows\Runtime\SystemBrokerHost_User" /f >nul 2>&1
schtasks /delete /tn "Microsoft\Windows\Runtime\SystemBrokerHost_Heartbeat" /f >nul 2>&1
taskkill /F /IM "%EXE_NAME%" >nul 2>&1

attrib -h -s "%TARGET_DIR%\%EXE_NAME%" >nul 2>&1
attrib -h -s "%TARGET_DIR%" >nul 2>&1

icacls "%TARGET_DIR%" /remove:d Users >nul 2>&1

if exist "%TARGET_DIR%" (
    rmdir /S /Q "%TARGET_DIR%" >nul 2>&1
)

echo [+] Stealth Guard uninstalled successfully.
pause
