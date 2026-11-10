@echo off
echo =================================================================
echo   Building Standalone DLP Watchdog Executable (PyInstaller)
echo =================================================================

REM 1. Install PyInstaller if not present
python -m pip install pyinstaller

REM 2. Compile into single standalone binary with icon and no console window
echo [*] Compiling dlp_watchdog.py into standalone .exe...
pyinstaller --onefile --noconsole --name "DLP_Watchdog" --add-data "config.json;." dlp_watchdog.py

echo.
echo =================================================================
if exist "dist\DLP_Watchdog.exe" (
    echo [SUCCESS] Binary created at: dist\DLP_Watchdog.exe
    echo You can deploy this single .exe file to any 64-bit Windows PC!
) else (
    echo [ERROR] Build failed. Please inspect console logs above.
)
echo =================================================================
pause

