@echo off
chcp 65001 > nul
echo ============================================
echo   Тактична ГІС - Встановлення залежностей
echo ============================================
echo.

echo [1/4] Створення віртуального середовища...
python -m venv venv
if errorlevel 1 (
    echo ПОМИЛКА: Не вдалося створити venv. Переконайтеся що Python встановлено.
    pause
    exit /b 1
)

echo [2/4] Активація середовища та встановлення пакетів...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ПОМИЛКА: Не вдалося встановити залежності.
    pause
    exit /b 1
)

echo [3/4] Створення директорій для даних...
if not exist "data" mkdir data
if not exist "data\tiles" mkdir data\tiles

echo [4/4] Перевірка встановлення...
python -c "import PyQt6; import PyQt6.QtWebEngineWidgets; import pyproj; import simplekml; import reportlab; print('OK')"
if errorlevel 1 (
    echo ПОПЕРЕДЖЕННЯ: Деякі пакети можуть бути недоступні.
) else (
    echo Всі пакети встановлено успішно!
)

echo.
echo ============================================
echo   Встановлення завершено успішно!
echo   Запустіть додаток: python main.py
echo ============================================
pause
