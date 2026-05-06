@echo off
chcp 65001 >nul
title ACAS Pro - Nginx TLS Setup
cls

echo ============================================
echo      ACAS Pro - Enterprise TLS Setup
echo ============================================
echo.

:: Check admin
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Run as Administrator
    pause
    exit /b 1
)

cd /d "%~dp0"

echo [1/6] Checking prerequisites...
where nginx >nul 2>&1
if errorlevel 1 (
    echo          Installing Nginx...
    powershell -Command "Invoke-WebRequest -Uri 'http://nginx.org/download/nginx-1.24.0.zip' -OutFile 'nginx.zip'"
    powershell -Command "Expand-Archive -Path 'nginx.zip' -DestinationPath 'C:\' -Force"
    ren "C:\nginx-1.24.0" "C:\nginx"
    setx PATH "%PATH%;C:\nginx" /M
    echo          [OK] Nginx installed to C:\nginx
) else (
    echo          [OK] Nginx found
)

echo [2/6] Creating SSL directory...
mkdir "C:\nginx\ssl" 2>nul
echo          [OK]

echo [3/6] Generating self-signed certificate...
cd "C:\nginx\ssl"
"C:\Program Files\OpenSSL-Win64\bin\openssl.exe" req -x509 -nodes -days 365 -newkey rsa:4096 ^
    -keyout key.pem -out cert.pem ^
    -subj "/CN=localhost/O=ACAS Pro/C=CN" ^
    -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1,IP:::1" 2>nul

if errorlevel 1 (
    echo          [WARNING] OpenSSL not found, using PowerShell...
    powershell -Command "$cert = New-SelfSignedCertificate -DnsName 'localhost','*.localhost' -CertStoreLocation cert:\LocalMachine\My -NotAfter (Get-Date).AddYears(1); $pwd = ConvertTo-SecureString -String 'temp' -Force -AsPlainText; Export-PfxCertificate -Cert $cert -FilePath cert.pfx -Password $pwd; Import-PfxCertificate -FilePath cert.pfx -CertStoreLocation cert:\LocalMachine\Root -Password $pwd"
)
echo          [OK]

echo [4/6] Copying configuration...
cd "%~dp0"
copy /Y nginx_tls.conf "C:\nginx\conf\nginx.conf" >nul
echo          [OK]

echo [5/6] Creating web root...
mkdir "C:\nginx\html\acas" 2>nul
xcopy /E /Y "..\web_static\*" "C:\nginx\html\acas\" >nul 2>&1
echo          [OK]

echo [6/6] Testing and starting Nginx...
cd "C:\nginx"
nginx -t
if errorlevel 1 (
    echo          [ERROR] Nginx config test failed
    pause
    exit /b 1
)

start nginx
echo          [OK] Nginx started

echo.
echo ============================================
echo      TLS Setup Complete
echo ============================================
echo.
echo Services:
echo   HTTPS: https://localhost
echo   HTTP:  http://localhost (redirects to HTTPS)
echo.
echo SSL Certificate: C:\nginx\ssl\cert.pem
echo Config: C:\nginx\conf\nginx.conf
echo.
echo To renew certificate, run: ssl_renew.sh
echo.
pause
