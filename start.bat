@echo off
setlocal
title Banco
cd /d "%~dp0"

if not exist "venv" (
    echo Creating local virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: cannot create venv. Verify that Python 3.10+ is installed.
        pause
        exit /b 1
    )
    echo Installing dependencies...
    venv\Scripts\python.exe -m pip install --upgrade pip -q
    venv\Scripts\python.exe -m pip install -r requirements.txt
)

if not exist ".env" (
    echo First run: starting setup wizard...
    venv\Scripts\python.exe scripts\setup_wizard.py
)

start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8501"

echo.
echo  Banco          http://127.0.0.1:8501
echo  Stage console  http://127.0.0.1:8501/console
echo  CTRL+C to stop.
echo.
venv\Scripts\python.exe -m app.server.main
pause
