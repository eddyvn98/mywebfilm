@echo off
title Cinema Home Server
echo Starting Cinema Backend...
cd /d "d:\trading\CinemaWeb"
start /b python webfilm.py
echo Waiting for server to initialize...
timeout /t 3 /nobreak > nul
echo Opening Cinema in Browser...
start "" "http://localhost:5000"
echo.
echo Cinema is running! Keep this window open.
echo To stop: Close this window or press Ctrl+C
pause > nul
