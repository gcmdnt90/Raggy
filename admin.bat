@echo off
setlocal
title Raggy — Admin Panel
cd /d "%~dp0"

:: Check venv
if not exist "venv" (
    echo ERROR: venv not found. Run start.bat first to set up the environment.
    pause
    exit /b 1
)

:: Open browser after 4 seconds (background)
start "" cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:8502"

:: Start admin panel
echo.
echo  Admin Panel will open automatically in your browser at http://localhost:8502
echo  Press CTRL+C to stop the server.
echo.
venv\Scripts\python.exe -m streamlit run app\admin.py --server.port 8502
pause
