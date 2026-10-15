@echo off
cd /d "%~dp0"
title Sentinel Live Video View
echo ========================================================
echo   Starting Live Video Detection with On-Screen Boxes
echo   Playing myvideo.mp4... (press 'q' on window to stop)
echo ========================================================
echo.
python cpu_video_demo.py --source myvideo.mp4 --show --realtime --dwell 1.5 || py cpu_video_demo.py --source myvideo.mp4 --show --realtime --dwell 1.5
echo.
pause
