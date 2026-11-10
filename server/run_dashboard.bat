@echo off
title DLP Management Incident Dashboard
cd /d "%~dp0"
echo ===============================================================
echo   Starting DLP Enterprise Management Incident Dashboard...
echo ===============================================================
start "" "http://127.0.0.1:5000"
python server.py
pause
