@echo off
setlocal enabledelayedexpansion
title Passive Thermal Shelter Platform — Setup & Launcher
echo ======================================================================
echo   PASSIVE THERMAL SHELTER ANALYSIS ^& RECOMMENDATION PLATFORM
echo   Universal Setup ^& One-Click Launcher for Any Windows Laptop
echo ======================================================================
echo.

:: 1. Verify Python availability
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not detected on your system PATH.
    echo.
    echo To run this platform on this laptop:
    echo 1. Download and install Python 3.10+ from: https://www.python.org/downloads/
    echo 2. IMPORTANT: Check the box "Add python.exe to PATH" during installation.
    echo 3. Re-run this setup script.
    echo.
    pause
    exit /b 1
)

echo [1/3] Checking Python Virtual Environment (.venv)...
if not exist ".venv\Scripts\activate.bat" (
    echo       Creating clean local virtual environment in .venv ...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo       Virtual environment created successfully.
) else (
    echo       Virtual environment .venv is ready.
)

:: 2. Install / Upgrade Dependencies
echo.
echo [2/3] Verifying and installing required packages from requirements.txt...
echo       (FastAPI, PyMAPDL, NumPy, Pandas, Plotly, ReportLab, SQLAlchemy)
.venv\Scripts\python -m pip install --quiet --upgrade pip
.venv\Scripts\pip install -r backend\requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Some dependencies failed to install. Retrying in verbose mode...
    .venv\Scripts\pip install -r backend\requirements.txt
)

:: 3. Run Diagnostic & Environment Check
echo.
echo [3/3] Running environment, database, and ANSYS MAPDL detection...
.venv\Scripts\python scripts\verify_setup.py

:: 4. Launch Platform
echo.
echo ======================================================================
echo   Starting Unified Platform on http://localhost:8000
echo   Opening dashboard in default web browser...
echo   Press Ctrl+C in this terminal window to stop the server.
echo ======================================================================
echo.

timeout /t 2 >nul
start "" http://localhost:8000
.venv\Scripts\python run.py

pause
