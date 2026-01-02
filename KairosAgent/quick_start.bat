@echo off
REM Kairos Agent - Windows Quick Start Script
REM ==========================================

echo.
echo ========================================
echo   KAIROS AGENT - Quick Start
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Set demo mode
set DEMO_MODE=true
set USER_GOALS=coding,learning

echo Installing dependencies...
pip install httpx fastapi uvicorn pydantic psutil >nul 2>&1

echo.
echo Starting demo (press Ctrl+C to stop)...
echo.

python demo.py --quick

pause
