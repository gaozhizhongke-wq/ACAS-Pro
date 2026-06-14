@echo off
chcp 65001 >nul
title ACAS Pro - Setup Backup Task
cls

echo ============================================
echo      ACAS Pro - Setup Auto Backup
echo ============================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 需要管理员权限运行
    echo 请右键以管理员身份运行此脚本
    pause
    exit /b 1
)

echo [1/3] Creating backup script...
(
echo @echo off
echo cd /d "%~dp0"
echo py -3.11 backup.py create --name auto_%%date:~-4,4%%%%date:~-10,2%%%%date:~-7,2%%
) > auto_backup.bat
echo          [OK]

echo [2/3] Creating scheduled task...

:: 每小时备份一次
schtasks /create /tn "ACAS-Pro-AutoBackup" /tr "\"%~dp0auto_backup.bat\"" /sc hourly /f >nul 2>&1

if errorlevel 1 (
    echo          [WARNING] 任务可能已存在
) else (
    echo          [OK] Task created
)

echo [3/3] Testing backup...
cd /d "%~dp0"
py -3.11 backup.py create --name test_init >nul 2>&1
if errorlevel 1 (
    echo          [WARNING] 备份测试失败
) else (
    echo          [OK] Backup test passed
)

echo.
echo ============================================
echo      Setup Complete
echo ============================================
echo.
echo Backup schedule: Every hour
echo Backup location: backups\
echo.
echo To remove: schtasks /delete /tn "ACAS-Pro-AutoBackup" /f
echo.
pause
