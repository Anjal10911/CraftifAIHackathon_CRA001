@echo off
setlocal
title Blind-Spot Watchdog Demo
echo ======================================================
echo    Blind-Spot Watchdog Demo (PipeGen Safety Add-on)
echo ======================================================
echo.
echo Running simulated demo feed (~22 seconds)...
echo Watches for simulated camera/pipeline failure and recovery.
echo.

python watchdog.py --demo --timeout 2 || py watchdog.py --demo --timeout 2

echo.
echo ======================================================
echo  Demo completed! Incident log written to:
echo  incident_log.jsonl
echo.
echo  Next steps:
echo  1. Open dashboard.html in your browser.
echo  2. Click "Load incident_log.jsonl" (or drag and drop it).
echo ======================================================
echo.
pause
