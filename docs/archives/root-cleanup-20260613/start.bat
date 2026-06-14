@echo off
chcp 65001 >nul
title ACAS Pro
cd /d "%~dp0"
echo [ACAS Pro] Starting...
echo.

:: Check Python
py -3.14 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.14 not found
    echo Please install Python 3.14
    pause
    exit /b 1
)

:: Load env
if exist .env (
    echo [OK] Loading environment
    for /f "tokens=1,* delims==" %%a in (.env) do (
        set "%%a=%%b"
    )
)

:: Start app
echo [OK] Starting main program
echo.
py -3.14 main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Program exited with error
    pause
)
