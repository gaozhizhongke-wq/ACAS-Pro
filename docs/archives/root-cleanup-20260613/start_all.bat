@echo off
chcp 65001 >nul
echo ==========================================
echo      ACAS Pro 完整启动脚本
echo ==========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

:: 创建输出目录
if not exist "output" mkdir output
if not exist "uploads" mkdir uploads

:: 检查依赖
echo [1/4] 检查依赖...
pip show flask flask-cors >nul 2>&1
if errorlevel 1 (
    echo      安装 Flask...
    pip install flask flask-cors -q
)

:: 启动视频 API 服务（后台）
echo [2/4] 启动视频剪辑 API 服务...
start "ACAS Video API" cmd /k "python video_api.py"

:: 启动 LLM API 服务（后台）
echo [3/4] 启动 LLM API 服务...
start "ACAS LLM API" cmd /k "python llm_api.py"

:: 等待服务启动
timeout /t 4 /nobreak >nul

:: 启动 Web 界面
echo [4/4] 启动 Web 界面...
echo.
echo ==========================================
echo      🚀 ACAS Pro 已启动！
echo ==========================================
echo.
echo 📱 Web 界面: http://localhost:8080
echo 🎬 视频 API:  http://localhost:5001
echo 🤖 LLM API:  http://localhost:5002
echo 📁 输出目录: %CD%\output\
echo.
echo 按任意键打开浏览器...
pause >nul

start http://localhost:8080

echo.
echo 服务正在运行，请勿关闭此窗口...
pause
