@echo off
chcp 65001 >nul
title ACAS Pro - 高智中科（北京）科技有限公司
cls

echo ============================================
echo      ACAS Pro - 自动获客系统专业版
echo      高智中科（北京）科技有限公司
echo ============================================
echo.
echo  版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
echo  All Rights Reserved.
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

:: 检查/创建 .env
if not exist ".env" (
    echo [INFO] Creating default configuration...
    (
        echo # ACAS Pro Production Configuration
        echo LLM_PROVIDER=deepseek
        echo LLM_API_KEY=sk-YOUR_DEEPSEEK_API_KEY_HERE
        echo LLM_MODEL=deepseek-chat
        echo DEBUG=false
        echo HOST=0.0.0.0
        echo PORT=5000
    ) > .env
    echo [OK] Configuration created
    echo.
)

:: 检查依赖
echo [1/3] Checking dependencies...
python -c "import flask, sqlalchemy" 2>nul
if errorlevel 1 (
    echo          Installing dependencies...
    pip install flask flask-cors sqlalchemy -q
)
echo          [OK] Dependencies ready

:: 初始化数据库
echo [2/3] Initializing database...
python -c "from database import get_db; db=get_db(); db.log('INFO', 'system', 'Server starting')" 2>nul
echo          [OK] Database ready

:: 验证配置
echo [3/3] Loading configuration...
python -c "from config import get_config; c=get_config(); print('          Provider: ' + c.llm.provider); print('          Model: ' + c.llm.model); print('          Enabled: ' + str(c.llm.enabled))"
echo          [OK] Configuration loaded

echo.
echo ============================================
echo      Server Starting
echo ============================================
echo.
echo Access URLs:
echo   - Health Check: http://localhost:5000/health
echo   - Web Interface: http://localhost:8080
echo   - API Base: http://localhost:5000/api/
echo.
echo Default Login:
echo   Username: admin
echo   Password: admin123
echo.
echo Press Ctrl+C to stop
echo.

:: 启动服务
python api_server.py

if errorlevel 1 (
    echo.
    echo [ERROR] Server crashed
    pause
)
