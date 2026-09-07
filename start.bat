@echo off
title Passive Thermal Shelter Analysis Platform
echo ======================================================================
echo   PASSIVE THERMAL SHELTER ANALYSIS ^& RECOMMENDATION PLATFORM
echo   PyAnsys-Driven Engineering Decision Support Suite
echo ======================================================================
echo.

set PY_EXE=python
if exist ".venv\Scripts\python.exe" (
    set PY_EXE=.venv\Scripts\python.exe
)

echo Starting Unified Platform on http://localhost:8000 ...
timeout /t 2 >nul
start "" http://localhost:8000
%PY_EXE% run.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NOTE] If dependencies or environment are missing, run setup_and_run.bat
    echo.
)
pause
