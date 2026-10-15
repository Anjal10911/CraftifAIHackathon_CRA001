@echo off
cd /d "%~dp0"
title Sentinel Video Inspector
echo ========================================================
echo       Workplace-Safety Sentinel: Video Detection
echo ========================================================
echo.

if not "%~1"=="" (
    echo Opening dropped video: "%~1"
    python cpu_video_demo.py --source "%~1" --show --realtime --dwell 2.0 || py cpu_video_demo.py --source "%~1" --show --realtime --dwell 2.0
    goto done
)

echo Opening file selector... please choose any video file.
python cpu_video_demo.py --select --show --realtime --dwell 2.0 || py cpu_video_demo.py --select --show --realtime --dwell 2.0

:done
echo.
pause
