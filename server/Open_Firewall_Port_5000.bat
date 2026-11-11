@echo off
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

title Open Firewall Port 5000 for DLP Dashboard
echo ================================================================
echo   Configuring Windows Firewall for DLP Central Dashboard
echo ================================================================
echo [*] Adding inbound rule for TCP Port 5000...
netsh advfirewall firewall delete rule name="Telegram DLP Dashboard (Port 5000)" >nul 2>&1
netsh advfirewall firewall add rule name="Telegram DLP Dashboard (Port 5000)" dir=in action=allow protocol=TCP localport=5000 profile=any >nul 2>&1

if %errorLevel% equ 0 (
    echo.
    echo ================================================================
    echo   [SUCCESS] Port 5000 is now open for incoming connections!
    echo   Teammate PCs can now send incident reports to this dashboard.
    echo ================================================================
) else (
    echo.
    echo [ERROR] Could not configure firewall. Please run as Administrator.
)
echo.
pause
