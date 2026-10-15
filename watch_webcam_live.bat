@echo off
title Sentinel Live Webcam View
echo ========================================================
echo   Starting Live Webcam Detection with On-Screen Boxes
echo   (Press 'q' inside the webcam window to stop)
echo ========================================================
echo.
python cpu_video_demo.py --source 0 --show --dwell 2.0
echo.
pause
