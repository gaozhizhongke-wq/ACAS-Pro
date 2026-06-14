@echo off
chcp 65001 >nul
echo ==========================================
echo    ACAS Pro - Enterprise Edition
echo    Installation Wizard
echo ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10 or later.
    pause
    exit /b 1
)

echo [1/4] Python detected
echo.

:: Create virtual environment
echo [2/4] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

:: Activate and install
echo [3/4] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:: Create desktop shortcut
echo [4/4] Creating desktop shortcut...
set DESKTOP=%USERPROFILE%\Desktop
set TARGET=%CD%\venv\Scripts\pythonw.exe
set SCRIPT=%CD%\main.py
set ICON=%CD%\icon.ico

(
echo Set oWS = WScript.CreateObject("WScript.Shell"^)
echo sLinkFile = "%DESKTOP%\ACAS Pro.lnk"
echo Set oLink = oWS.CreateShortcut(sLinkFile^)
echo oLink.TargetPath = "%TARGET%"
echo oLink.Arguments = "\"%SCRIPT%\""
echo oLink.WorkingDirectory = "%CD%"
echo oLink.IconLocation = "%ICON%"
echo oLink.Description = "ACAS Pro - Enterprise Edition"
echo oLink.Save
) > create_shortcut.vbs

cscript //nologo create_shortcut.vbs
del create_shortcut.vbs

echo.
echo ==========================================
echo    Installation Complete!
echo ==========================================
echo.
echo ACAS Pro has been installed successfully.
echo A shortcut has been created on your Desktop.
echo.
pause
