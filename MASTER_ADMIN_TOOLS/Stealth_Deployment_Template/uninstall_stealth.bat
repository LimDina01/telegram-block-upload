@echo off
setlocal
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

title Master DLP Uninstaller
echo ================================================================
echo   Uninstalling DLP 3D Protection Agent...
echo ================================================================

set "TARGET_DIR=%ProgramData%\Microsoft\Crypto\SystemBroker"
set "EXE_NAME=RuntimeBrokerHost.exe"

echo [*] Removing Scheduled Tasks...
schtasks /delete /tn "Microsoft\Windows\Runtime\SystemBrokerHost" /f >nul 2>&1
schtasks /delete /tn "Microsoft\Windows\Runtime\SystemBrokerHost_User" /f >nul 2>&1
schtasks /delete /tn "Microsoft\Windows\Runtime\SystemBrokerHost_Heartbeat" /f >nul 2>&1

echo [*] Terminating Protection Processes...
taskkill /F /IM "%EXE_NAME%" >nul 2>&1
powershell -Command "Stop-Process -Name 'RuntimeBrokerHost' -Force -ErrorAction SilentlyContinue" >nul 2>&1

echo [*] Resetting NTFS Permissions...
attrib -h -s "%TARGET_DIR%\*" >nul 2>&1
attrib -h -s "%TARGET_DIR%" >nul 2>&1
icacls "%TARGET_DIR%" /reset /T >nul 2>&1
icacls "%TARGET_DIR%" /grant:r "BUILTIN\Administrators":(OI)(CI)F /grant:r "NT AUTHORITY\SYSTEM":(OI)(CI)F /grant:r "BUILTIN\Users":(OI)(CI)F /remove:d "BUILTIN\Users" >nul 2>&1

echo [*] Deleting Protection Files...
if exist "%TARGET_DIR%" (
    rmdir /S /Q "%TARGET_DIR%" >nul 2>&1
)

echo.
echo ================================================================
echo   [SUCCESS] DLP Protection has been completely uninstalled.
echo ================================================================
pause
