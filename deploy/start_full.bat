@echo off
chcp 65001 >nul 2>&1
title ACAS Pro - Full Service Launcher
echo ==========================================
echo   ACAS Pro 企业级自动获客系统
echo   版权所有 (c) 2026 高智中科（北京）科技有限公司
echo   Full Service Launcher
echo ==========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.11+
    pause
    exit /b 1
)

REM 加载环境变量
if exist .env (
    echo [INFO] Loading .env configuration...
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" (
            set "%%a=%%b"
        )
    )
) else (
    echo [WARN] .env file not found, using defaults
)

REM 创建必要目录
if not exist logs mkdir logs
if not exist backups mkdir backups
if not exist data mkdir data

echo.
echo [1/5] Pre-deployment check...
python -c "from deploy.deploy_manager import DeployManager; r=DeployManager().pre_check(); print('PASS' if r.success else 'FAIL: '+r.message)"
if errorlevel 1 (
    echo [WARN] Pre-check failed, continuing anyway...
)

echo.
echo [2/5] Starting API Server (port 5002)...
start "ACAS-API" /min python api_server_v2.py --port 5002
timeout /t 3 /nobreak >nul

echo [3/5] Starting Health Monitor...
start "ACAS-Health" /min python -c "from monitoring.health_check import HealthChecker; import time; h=HealthChecker(); [time.sleep(60) or print(h.format_report(h.run_all_checks())) for _ in iter(int, 1)]"

echo [4/5] Starting Backup Scheduler...
start "ACAS-Backup" /min python -c "from dr.backup_manager import BackupManager; import time; m=BackupManager(); [time.sleep(3600) or m.backup_database() for _ in iter(int, 1)]"

echo [5/5] Verifying services...
timeout /t 5 /nobreak >nul
python -c "import urllib.request; r=urllib.request.urlopen('http://localhost:5002/api/health',timeout=5); print('API Health:', r.read().decode()[:80])" 2>nul
if errorlevel 1 (
    echo [WARN] API health check failed - service may need more time to start
) else (
    echo [OK] All services started successfully
)

echo.
echo ==========================================
echo   Services running:
echo   - API Server:     http://localhost:5002
echo   - Web Dashboard:  http://localhost:5002/dashboard
echo   - Health Check:   http://localhost:5002/api/health
echo ==========================================
echo.
echo Press Ctrl+C to stop all services...
echo.

REM 等待用户中断
pause
