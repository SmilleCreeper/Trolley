@echo off
cd /d "%~dp0"
start /B python server\server.py
timeout /t 2 /nobreak >nul
node_modules\.bin\electron.cmd .
taskkill /F /IM python.exe >nul 2>&1
