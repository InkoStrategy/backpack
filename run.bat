@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Run setup.bat first!
    pause
    exit /b 1
)
echo Starting TacGIS...
python main.py
pause
