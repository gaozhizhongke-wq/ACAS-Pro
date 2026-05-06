@echo off
chcp 65001 >nul
title ACAS Pro LLM Service
cls

echo ==========================================
echo      ACAS Pro LLM API Service v2
echo ==========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    echo Please install Python 3.11 or higher
    pause
    exit /b 1
)

:: 检查 .env 文件
if not exist ".env" (
    echo [WARNING] .env file not found
    echo Creating from template...
    (
        echo # ACAS Pro Configuration
        echo LLM_PROVIDER=deepseek
        echo LLM_API_KEY=sk-YOUR_DEEPSEEK_API_KEY_HERE
        echo LLM_MODEL=deepseek-chat
        echo DEBUG=false
        echo HOST=0.0.0.0
        echo PORT=5002
    ) > .env
    echo [OK] Created .env with default config
    echo.
)

:: 检查依赖
echo [1/3] Checking dependencies...
python -c "import flask" 2>nul
if errorlevel 1 (
    echo          Installing Flask...
    pip install flask flask-cors -q
)
echo          [OK] Dependencies ready

:: 验证配置
echo [2/3] Loading configuration...
python -c "from config import get_config; c=get_config(); print(f'         Provider: {c.llm.provider}'); print(f'         Model: {c.llm.model}'); print(f'         Enabled: {c.llm.enabled}')"
if errorlevel 1 (
    echo [ERROR] Failed to load configuration
    pause
    exit /b 1
)
echo          [OK] Configuration loaded

:: 启动服务
echo [3/3] Starting service...
echo.
echo ==========================================
echo      Service Starting
echo ==========================================
echo.
echo Health Check: http://localhost:5002/health
echo API Docs:     http://localhost:5002/api/config
echo Chat API:     http://localhost:5002/api/chat
echo.
echo Press Ctrl+C to stop
echo.

python llm_api_v2.py

if errorlevel 1 (
    echo.
    echo [ERROR] Service crashed
    pause
)
