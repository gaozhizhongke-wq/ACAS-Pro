@echo off
chcp 65001 >nul
echo ==========================================
echo      ACAS Pro 视频剪辑 API 服务
echo ==========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

:: 检查依赖
echo [1/2] 检查依赖...
pip show flask flask-cors >nul 2>&1
if errorlevel 1 (
    echo      安装 Flask...
    pip install flask flask-cors -q
)

:: 检查 FFmpeg
echo [2/2] 检查 FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️  未找到 FFmpeg！请先运行 install_ffmpeg.bat 安装
    echo.
    choice /C YN /M "是否继续启动（部分功能将不可用）"
    if errorlevel 2 exit /b 1
)

echo.
echo ==========================================
echo      🚀 启动视频剪辑 API 服务...
echo      地址: http://localhost:5001
echo ==========================================
echo.

python video_api.py

pause
