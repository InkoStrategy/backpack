@echo off
cd /d "%~dp0"

echo ============================================
echo   TacGIS - Installing dependencies...
echo ============================================
echo.

echo [1/4] Creating virtual environment...
py -m venv venv
if errorlevel 1 (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Python not found. Install Python 3.13 from python.org
        pause
        exit /b 1
    )
)
echo   OK

echo [2/4] Installing packages (this takes 3-5 minutes)...
call venv\Scripts\activate.bat
py -m pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install packages.
    pause
    exit /b 1
)
echo   OK

echo [3/4] Creating data directories...
if not exist "data" mkdir data
if not exist "data\tiles" mkdir data\tiles
echo   OK

echo [4/4] Checking installation...
python -c "import PyQt6; import pyproj; print('All packages OK')"
if errorlevel 1 (
    echo WARNING: Some packages may be missing.
) else (
    echo   OK
)

echo.
echo ============================================
echo   Setup complete! Run the app: run.bat
echo ============================================
pause
