@echo off
chcp 65001 >nul
title ACAS Pro - Build Installer
cls

echo ============================================
echo      ACAS Pro - Build Installer
echo ============================================
echo.

set BUILD_DIR=dist\ACAS-Pro
set VERSION=2.0.0

echo [1/5] Cleaning previous build...
if exist dist rmdir /s /q dist
mkdir %BUILD_DIR%
echo          [OK]

echo [2/5] Copying application files...
xcopy /s /y /q *.py %BUILD_DIR%\
xcopy /s /y /q *.bat %BUILD_DIR%\
xcopy /s /y /q .env.example %BUILD_DIR%\
xcopy /s /y /q web_static %BUILD_DIR%\web_static\
xcopy /s /y /q src %BUILD_DIR%\src\
echo          [OK]

echo [3/5] Creating startup scripts...
(
echo @echo off
echo chcp 65001 ^>nul
echo echo Starting ACAS Pro...
echo start http://localhost:8080
echo start_production.bat
) > %BUILD_DIR%\START.bat

echo          [OK]

echo [4/5] Creating README...
(
echo # ACAS Pro v%VERSION%
echo.
echo ## 快速开始
echo.
echo 1. 双击运行 `START.bat`
echo 2. 浏览器自动打开 http://localhost:8080
echo 3. 默认登录: admin / admin123
echo.
echo ## 系统要求
echo - Windows 10/11
echo - Python 3.11+
echo - 内存: 4GB+
echo - 磁盘: 500MB+
echo.
echo ## 配置说明
echo 编辑 `.env` 文件配置 LLM API Key
echo.
echo ## 支持
echo 技术支持: support@acas.pro
) > %BUILD_DIR%\README.txt

echo          [OK]

echo [5/5] Creating ZIP package...
powershell -Command "Compress-Archive -Path '%BUILD_DIR%' -DestinationPath 'dist\ACAS-Pro-v%VERSION%.zip' -Force"
echo          [OK]

echo.
echo ============================================
echo      Build Complete
echo ============================================
echo.
echo Output: dist\ACAS-Pro-v%VERSION%.zip
echo Size: 
for %%I in (dist\ACAS-Pro-v%VERSION%.zip) do echo          %%~zI bytes
echo.
pause
