@echo off
chcp 65001 >nul
title ACAS Pro - HTTPS Setup
echo ============================================
echo      ACAS Pro - HTTPS 快速配置
echo ============================================
echo.

cd /d "%~dp0"

:: 检查管理员权限
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 需要管理员权限运行
    pause
    exit /b 1
)

echo [1/4] Installing mkcert for local HTTPS...
where mkcert >nul 2>&1
if errorlevel 1 (
    echo          Downloading mkcert...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-windows-amd64.exe' -OutFile 'mkcert.exe'"
    mkcert.exe -install
    echo          [OK] mkcert installed
) else (
    echo          [OK] mkcert already installed
)

echo [2/4] Generating SSL certificates...
mkcert.exe -cert-file cert.pem -key-file key.pem localhost 127.0.0.1 ::1 192.168.*.* 10.*.*.*
echo          [OK] Certificates generated

echo [3/4] Creating HTTPS server...
(
echo #!/usr/bin/env python3
echo # HTTPS wrapper for ACAS Pro
echo import ssl, subprocess, sys, os
echo from http.server import HTTPServer, SimpleHTTPRequestHandler
echo from urllib.parse import urlparse
echo import threading, json, http.client
echo.
echo # API proxy to Flask
echo class ProxyHandler(SimpleHTTPRequestHandler):
echo     def do_GET(self^):
echo         if self.path.startswith('/api/'^) or self.path == '/health':
echo             self._proxy_to_api(^)
echo         else:
echo             super(^).do_GET(^)
echo     
echo     def do_POST(self^):
echo         if self.path.startswith('/api/'^):
echo             self._proxy_to_api(^)
echo         else:
echo             super(^).do_POST(^)
echo     
echo     def _proxy_to_api(self^):
echo         try:
echo             conn = http.client.HTTPConnection('localhost', 5000, timeout=10^)
echo             content_length = int(self.headers.get('Content-Length', 0^)^)
echo             body = self.rfile.read(content_length^) if content_length ^> 0 else None
echo             
echo             headers = {k: v for k, v in self.headers.items(^) if k.lower(^) not in ['host', 'content-length']}
echo             conn.request(self.command, self.path, body=body, headers=headers^)
echo             
echo             resp = conn.getresponse(^)
echo             self.send_response(resp.status^)
echo             for k, v in resp.getheaders(^):
echo                 if k.lower(^) not in ['transfer-encoding', 'content-length']:
echo                     self.send_header(k, v^)
echo             self.send_header('Content-Length', resp.length^)
echo             self.end_headers(^)
echo             self.wfile.write(resp.read(^)^)
echo         except Exception as e:
echo             self.send_error(502, f'API Error: {e}'^)
echo     
echo     def end_headers(self^):
echo         self.send_header('Strict-Transport-Security', 'max-age=31536000'^)
echo         super(^).end_headers(^)
echo.
echo if __name__ == '__main__':
echo     os.chdir('web_static'^)
echo     server = HTTPServer(('0.0.0.0', 8443^), ProxyHandler^)
echo     server.socket = ssl.wrap_socket(server.socket, keyfile='../key.pem', certfile='../cert.pem', server_side=True^)
echo     print('HTTPS Server running on https://localhost:8443'^)
echo     server.serve_forever(^)
) > https_server.py
echo          [OK] HTTPS server created

echo [4/4] Creating startup script...
(
echo @echo off
echo chcp 65001 ^>nul
echo echo ============================================
echo echo      ACAS Pro - Secure Mode (HTTPS^)
echo echo ============================================
echo echo.
echo echo Starting API server...
echo start "ACAS API" cmd /k "py -3.11 api_server.py"
echo echo Waiting for API to start...
echo timeout /t 3 /nobreak ^>nul
necho echo.
echo echo Starting HTTPS server on https://localhost:8443
echo py -3.11 https_server.py
) > START_SECURE.bat
echo          [OK] Startup script created

echo.
echo ============================================
echo      HTTPS Setup Complete
echo ============================================
echo.
echo Usage:
echo   1. Run START_SECURE.bat (as Admin^)
echo   2. Open https://localhost:8443
echo   3. Accept the self-signed certificate
echo.
echo Note: For production, replace with real SSL certificate
echo.
pause
