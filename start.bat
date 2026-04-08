@echo off
setlocal
title Raggy — Start
cd /d "%~dp0"

:: Create venv if needed
if not exist "venv" (
    echo Creating local virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: cannot create venv. Verify that Python 3.11+ is installed.
        pause
        exit /b 1
    )
    echo Installing dependencies in local venv...
    venv\Scripts\python.exe -m pip install --upgrade pip -q
    venv\Scripts\python.exe -m pip install -r requirements.txt
)

:: First run — setup wizard
if not exist "knowledge_base\chroma_db" (
    echo First run: starting setup wizard...
    venv\Scripts\python.exe scripts\setup_wizard.py
)

:: Open browser after 4 seconds (background)
start "" cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:8501"

:: Start Raggy
echo.
echo  Raggy will open automatically in your browser at http://localhost:8501
echo  Press CTRL+C to stop the server.
echo.
venv\Scripts\python.exe -m streamlit run app\main.py
pause
