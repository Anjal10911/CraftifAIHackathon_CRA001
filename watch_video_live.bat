@echo off
title Sentinel Live Video View
echo ========================================================
echo   Starting Live Video Detection with On-Screen Boxes
echo   (Press 'q' inside the video window to stop)
echo ========================================================
echo.
python cpu_video_demo.py --source myvideo.mp4 --show --realtime --dwell 1.5
echo.
pause
