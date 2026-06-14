@echo off
chcp 65001 >nul
title ACAS Pro v2.1 - 高智中科（北京）科技有限公司 - 安全加固版
cls

echo ================================================================================
echo      ACAS Pro v2.1 - 自动获客系统专业版
echo      安全加固版 - Phase 1 整改完成
echo ================================================================================
echo  版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
echo  All Rights Reserved.
echo ================================================================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] 建议以管理员身份运行以获得完整功能
echo.
)

:: 检查 Python
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11 未找到，请先安装
    pause
    exit /b 1
)

:: 创建必要目录
echo [1/5] 初始化目录结构...
if not exist "logs" mkdir logs
if not exist ".keys" mkdir .keys
if not exist "certs" mkdir certs
echo          [OK]

:: 检查/创建 .env
echo [2/5] 检查环境配置...
if not exist ".env" (
    echo          创建默认配置...
    (
        echo # ACAS Pro v2.1 - Production Configuration
        echo # 高智中科（北京）科技有限公司
        echo.
        echo # 安全警告：生产环境必须修改以下配置！
        echo # ===========================================
        echo.
        echo # JWT 配置（首次启动自动生成）
        echo JWT_SECRET_FILE=.keys/jwt_secret.key
        echo.
        echo # CORS 白名单（逗号分隔，生产环境必须限制）
        echo ALLOWED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
        echo.
        echo # SSL 证书（生产环境必须配置）
        echo # SSL_CERT_FILE=certs/your-domain.crt
        echo # SSL_KEY_FILE=certs/your-domain.key
        echo.
        echo # 数据库（默认 SQLite，生产环境请使用 PostgreSQL）
        echo DATABASE_URL=sqlite:///acas_pro.db
        echo.
        echo # 日志级别
        echo LOG_LEVEL=INFO
    ) > .env
    echo          [OK] 配置已创建，请根据生产环境修改！
) else (
    echo          [OK] 配置已存在
)

:: 安装依赖
echo [3/5] 检查依赖...
py -3.11 -c "import flask, jwt, sqlalchemy" 2>nul
if errorlevel 1 (
    echo          安装依赖...
    py -3.11 -m pip install flask flask-cors pyjwt sqlalchemy -q
)
echo          [OK]

:: 初始化安全体系
echo [4/5] 初始化安全体系...
py -3.11 -c "from security import init_security; init_security()" 2>nul
if errorlevel 1 (
    echo          [WARNING] 安全初始化可能需要首次运行
)
echo          [OK]

:: 检查密钥
echo [5/5] 检查密钥状态...
if not exist ".keys\jwt_secret.key" (
    echo          [WARNING] JWT 密钥未生成，将在首次启动时创建
) else (
    echo          [OK] 密钥已存在
)

echo.
echo ================================================================================
echo      安全警告
echo ================================================================================
echo.
echo  [!] 默认管理员账号: admin / admin123
echo  [!] 首次登录后必须修改密码
echo  [!] 生产环境必须配置 SSL 证书
echo  [!] 生产环境必须使用 PostgreSQL 数据库
echo.
echo ================================================================================
echo      启动服务
echo ================================================================================
echo.
echo  API 地址:      http://localhost:5000
echo  健康检查:      http://localhost:5000/health
echo  Web 界面:      http://localhost:8080
echo.
echo  按 Ctrl+C 停止服务
echo.

:: 启动服务
py -3.11 api_server_v2.py

if errorlevel 1 (
    echo.
    echo [ERROR] 服务启动失败，请检查日志: logs/api.log
    pause
)
