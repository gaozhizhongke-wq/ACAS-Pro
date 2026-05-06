@echo off
chcp 65001 >nul
echo ==========================================
echo      FFmpeg 快速安装工具
echo ==========================================
echo.

set "FFMPEG_DIR=%USERPROFILE%\ffmpeg"
set "ZIP_FILE=%TEMP%\ffmpeg.zip"

echo [1/4] 正在下载 FFmpeg...
echo      来源: 华为云镜像
echo      大小: 约 140MB
echo.

powershell -Command "Invoke-WebRequest -Uri 'https://mirrors.huaweicloud.com/ffmpeg/6.0/ffmpeg-6.0-full_build.zip' -OutFile '%ZIP_FILE%' -TimeoutSec 300"

if not exist "%ZIP_FILE%" (
    echo [错误] 下载失败，尝试备用源...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/GyanD/codexffmpeg/releases/download/6.0/ffmpeg-6.0-full_build.zip' -OutFile '%ZIP_FILE%' -TimeoutSec 300"
)

if not exist "%ZIP_FILE%" (
    echo [错误] 下载失败，请手动下载:
    echo       https://www.gyan.dev/ffmpeg/builds/
    pause
    exit /b 1
)

echo [2/4] 正在解压...
if exist "%FFMPEG_DIR%" rmdir /s /q "%FFMPEG_DIR%"
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%FFMPEG_DIR%' -Force"

echo [3/4] 正在配置环境变量...
setx PATH "%PATH%;%FFMPEG_DIR%\ffmpeg-6.0-full_build\bin" >nul 2>&1

echo [4/4] 清理临时文件...
del "%ZIP_FILE%" 2>nul

echo.
echo ==========================================
echo      ✅ FFmpeg 安装完成！
echo ==========================================
echo.
echo 安装路径: %FFMPEG_DIR%\ffmpeg-6.0-full_build
echo.
echo 请重新打开 PowerShell 或命令提示符
echo 然后运行: ffmpeg -version
echo.
echo 现在可以运行视频剪辑 Agent:
echo    python video_agent.py
echo.
pause
