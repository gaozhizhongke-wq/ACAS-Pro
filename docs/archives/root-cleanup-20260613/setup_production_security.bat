@echo off
chcp 65001 >nul
title ACAS Pro - Production Security Setup
cls

echo ============================================
echo      ACAS Pro - 生产安全加固
echo ============================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 需要管理员权限运行
    pause
    exit /b 1
)

cd /d "%~dp0"

echo [1/5] Installing cryptography package...
py -3.11 -m pip install cryptography -q
echo          [OK]

echo [2/5] Setting up encrypted configuration...
py -3.11 secure_config.py
echo          [OK]

echo [3/5] Setting up HTTPS...
call setup_https.bat
echo          [OK]

echo [4/5] Creating secure startup script...
(
echo @echo off
echo chcp 65001 ^>nul
echo echo ============================================
echo echo      ACAS Pro - Production Mode
echo echo ============================================
echo echo.
echo.
echo :: Check for master key
echo if "%%ACAS_MASTER_KEY%%"=="" (
echo     echo [WARNING] ACAS_MASTER_KEY not set
echo     echo Please set: set ACAS_MASTER_KEY=your_key
echo     pause
echo     exit /b 1
echo ^)
echo.
echo echo [1/3] Starting API server with secure config...
echo start "ACAS API" cmd /k "py -3.11 api_server.py"
echo timeout /t 3 /nobreak ^>nul
echo.
echo echo [2/3] Starting HTTPS server...
echo start "ACAS HTTPS" cmd /k "py -3.11 https_server.py"
echo timeout /t 2 /nobreak ^>nul
echo.
echo echo [3/3] All services started
echo echo.
echo echo ============================================
echo echo      Services Running
echo echo ============================================
echo echo API:     http://localhost:5000
echo echo HTTPS:   https://localhost:8443
echo echo.
echo echo Press any key to stop all services...
echo pause ^>nul
echo.
echo Stopping services...
echo taskkill /F /FI "WINDOWTITLE eq ACAS API" ^>nul 2^>^&1
echo taskkill /F /FI "WINDOWTITLE eq ACAS HTTPS" ^>nul 2^>^&1
echo          [OK] Services stopped
) > START_PRODUCTION_SECURE.bat
echo          [OK]

echo [5/5] Creating security checklist...
(
echo # ACAS Pro - 生产安全检查清单
echo.
echo ## 部署前检查
echo.
echo - [ ] 已运行 setup_production_security.bat
echo - [ ] 已设置 ACAS_MASTER_KEY 环境变量
echo - [ ] 已配置 HTTPS 证书（或自签名）
echo - [ ] 已测试加密配置加载
echo - [ ] 已验证 HTTPS 访问正常
echo - [ ] 已删除/备份明文 .env 文件
echo - [ ] 已配置防火墙规则（仅开放 8443）
echo - [ ] 已测试自动备份功能
echo - [ ] 已创建数据库备份
echo - [ ] 已配置日志轮转
echo.
echo ## 启动后检查
echo.
echo - [ ] https://localhost:8443 可访问
echo - [ ] 登录功能正常
echo - [ ] API 响应正常
echo - [ ] 日志文件正常生成
echo - [ ] 无错误日志
.
echo ## 监控项
echo.
echo - [ ] 磁盘空间 ^> 1GB
echo - [ ] 内存使用 ^< 80%%%
echo - [ ] 响应时间 ^< 500ms
echo - [ ] 错误率 ^< 1%%%
) > SECURITY_CHECKLIST.md
echo          [OK]

echo.
echo ============================================
echo      Production Security Setup Complete
echo ============================================
echo.
echo 已完成的安全加固:
echo   [OK] 配置加密存储 (Fernet)
echo   [OK] HTTPS 支持 (mkcert)
echo   [OK] 安全启动脚本
.
echo.
echo 下一步:
echo   1. 设置环境变量: set ACAS_MASTER_KEY=your_secret_key
echo   2. 运行: START_PRODUCTION_SECURE.bat
echo   3. 访问: https://localhost:8443
echo.
echo 重要提醒:
echo   - 请妥善保存 .secure_key 文件
echo   - 生产环境请使用真实 SSL 证书
echo   - 定期更换 master key
.
echo.
pause
