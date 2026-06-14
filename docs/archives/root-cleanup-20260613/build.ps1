# ACAS Pro Build Script
$ErrorActionPreference = "Stop"

$BUILD_DIR = "dist\ACAS-Pro"
$VERSION = "2.0.0"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "     ACAS Pro - Build Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/5] Cleaning previous build..."
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
}
New-Item -ItemType Directory -Path $BUILD_DIR | Out-Null
Write-Host "      [OK]" -ForegroundColor Green

Write-Host "[2/5] Copying application files..."
Copy-Item "*.py" $BUILD_DIR\ -Force
Copy-Item "*.bat" $BUILD_DIR\ -Force
Copy-Item ".env" $BUILD_DIR\ -Force -ErrorAction SilentlyContinue
Copy-Item ".env.example" $BUILD_DIR\ -Force -ErrorAction SilentlyContinue
Copy-Item "web_static" $BUILD_DIR\ -Recurse -Force
Copy-Item "src" $BUILD_DIR\ -Recurse -Force
Write-Host "      [OK]" -ForegroundColor Green

Write-Host "[3/5] Creating startup scripts..."
@"
@echo off
chcp 65001 >nul
echo.
echo ================================================================================
echo  ACAS Pro v$VERSION - 自动获客系统专业版
echo ================================================================================
echo  版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
echo ================================================================================
echo.
echo 正在启动 ACAS Pro...
echo.
start http://localhost:8080
call start_production.bat
"@ | Out-File -Encoding utf8 "$BUILD_DIR\START.bat"
Write-Host "      [OK]" -ForegroundColor Green

Write-Host "[4/5] Creating README..."
@"
================================================================================
 ACAS Pro v$VERSION
 自动获客系统专业版
================================================================================

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.

================================================================================
 快速开始
================================================================================

1. 双击运行 START.bat
2. 浏览器自动打开 http://localhost:8080
3. 默认登录: admin / admin123

================================================================================
 系统要求
================================================================================

- Windows 10/11
- Python 3.11+
- 内存: 4GB+
- 磁盘: 500MB+

================================================================================
 配置说明
================================================================================

编辑 .env 文件配置 LLM API Key 和其他参数

================================================================================
 技术支持
================================================================================

高智中科（北京）科技有限公司

================================================================================
"@ | Out-File -Encoding utf8 "$BUILD_DIR\README.txt"
Write-Host "      [OK]" -ForegroundColor Green

Write-Host "[5/5] Creating ZIP package..."
$zipPath = "dist\ACAS-Pro-v$VERSION.zip"
Compress-Archive -Path $BUILD_DIR -DestinationPath $zipPath -Force
$size = (Get-Item $zipPath).Length
Write-Host "      [OK]" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "     Build Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Output: $zipPath"
Write-Host "Size: $([math]::Round($size/1MB, 2)) MB"
Write-Host ""
