@echo off
setlocal enabledelayedexpansion

title Passive Shelter Thermal Platform - Setup

echo ======================================================================
echo   PASSIVE SHELTER THERMAL PLATFORM - 1-CLICK INSTALLER
echo   PyAnsys MAPDL Transient Simulation Engine
echo ======================================================================
echo.

:: Check for Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found on your system PATH!
    echo Please install Python 3.10 or newer from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Run Python setup program
python setup_platform.py %*
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Setup encountered an issue. Please review the output above.
    pause
    exit /b %errorlevel%
)

echo.
echo Press any key to exit setup, or launch the app using start.bat
pause
