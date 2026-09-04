@echo off
title Passive Thermal Shelter Analysis Platform
echo ======================================================================
echo   PASSIVE THERMAL SHELTER ANALYSIS ^& RECOMMENDATION PLATFORM
echo   PyAnsys-Driven Engineering Decision Support Suite
echo ======================================================================
echo.

echo Starting Platform Backend and Dashboard on http://localhost:8000 ...
timeout /t 2 >nul
start "" http://localhost:8000
python run.py
pause
