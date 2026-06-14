@echo off
echo Stopping ACAS-Pro...

REM Stop nginx
cd /d "C:\nginx\nginx-1.26.2"
nginx.exe -s quit 2>nul

REM Stop Redis
"C:\redis\redis-cli.exe" SHUTDOWN NOSAVE 2>nul

echo ACAS-Pro stopped.
pause
