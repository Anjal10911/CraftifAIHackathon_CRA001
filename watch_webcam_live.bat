@echo off
cd /d "%~dp0"
title Sentinel Live Webcam View
echo ========================================================
echo   Starting Live Webcam Detection (OpenCV HOG Sentinel)
echo   Connecting to webcam... (press 'q' on window to stop)
echo ========================================================
echo.
python cpu_video_demo.py --source 0 --show --dwell 2.0 || py cpu_video_demo.py --source 0 --show --dwell 2.0
echo.
pause
