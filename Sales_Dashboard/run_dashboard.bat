@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Python was not found. Install Python 3.10 or newer and try again.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating the project environment...
    py -m venv .venv
    if errorlevel 1 (
        echo Could not create the virtual environment.
        pause
        exit /b 1
    )
)

echo Checking dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed. Check your internet connection and try again.
    pause
    exit /b 1
)

echo Starting Pulseboard at http://127.0.0.1:5000
start "Pulseboard server" cmd /k ""%~dp0.venv\Scripts\python.exe" "%~dp0app.py""
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5000
endlocal