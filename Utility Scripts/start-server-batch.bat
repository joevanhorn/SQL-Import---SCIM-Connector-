@echo off
REM Okta SCIM SQL Connector - Quick Start Script
REM This script activates the virtual environment and starts the SCIM server

echo ========================================
echo Okta SCIM SQL Connector
echo ========================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo.
    echo Please run: python -m venv venv
    echo Then: pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if .env file exists
if not exist ".env" (
    echo.
    echo Warning: .env file not found!
    echo.
    echo Please create .env file from .env.example
    echo Example: copy .env.example .env
    echo Then edit .env with your configuration
    echo.
    pause
    exit /b 1
)

REM Start the server
echo.
echo Starting SCIM server...
echo.
echo Press Ctrl+C to stop the server
echo.

python inbound_app.py

REM If server exits, pause so we can see any errors
echo.
echo Server stopped.
pause