@echo off
echo Starting ACAS-Pro HTTPS proxy...
echo.
echo Checking prerequisites...

REM Check nginx
if not exist "C:\nginx\nginx-1.26.2\nginx.exe" (
    echo ERROR: nginx not found at C:\nginx\nginx-1.26.2\nginx.exe
    pause
    exit /b 1
)

REM Check SSL certs
if not exist "C:\nginx\ssl\server.crt" (
    echo ERROR: SSL certificate not found at C:\nginx\ssl\server.crt
    pause
    exit /b 1
)

REM Start Redis if not running
redis-cli PING >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Redis...
    start "Redis" /B "C:\redis\redis-server.exe"
    timeout /t 2 /nobreak >nul
)

REM Start ACAS-Pro backend (Flask on port 8000)
echo Starting ACAS-Pro backend...
start "ACAS-Pro" /B python web_app.py

REM Wait for backend to be ready
echo Waiting for backend...
timeout /t 3 /nobreak >nul

REM Start nginx
echo Starting nginx...
cd /d "C:\nginx\nginx-1.26.2"
nginx.exe -c "C:\nginx\conf\acas-pro.conf"

echo.
echo ACAS-Pro is running:
echo   HTTPS: https://localhost
echo   HTTP:  http://localhost (redirects to HTTPS)
echo   API:   http://localhost:8000/api/ (direct, bypasses nginx)
echo.
echo To stop: run stop-acas-pro.bat
pause
