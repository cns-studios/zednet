@echo off
echo ======================================
echo ZedNet Security-First Setup
echo ======================================

python --version
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo ======================================
echo Setup complete!
echo ======================================
echo.
echo To start ZedNet:
echo   1. venv\Scripts\activate.bat
echo   2. python main.py
echo.
echo WARNING: Use a VPN before starting!
echo.
pause