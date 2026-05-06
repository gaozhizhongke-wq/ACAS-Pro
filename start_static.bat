@echo off
chcp 65001 >nul
title ACAS Pro
cd /d "%~dp0\web_static"
echo [ACAS Pro] Starting...
echo [OK] Open browser: http://localhost:8080
echo.
py -3.14 -m http.server 8080
