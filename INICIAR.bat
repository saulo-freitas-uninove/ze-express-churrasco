@echo off
chcp 65001 >nul
title Ze Express Churrasco - servidor (porta 8170)
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python nao encontrado. Instale o Python 3 em python.org marcando "Add to PATH".
  pause
  exit /b 1
)
REM Derruba qualquer servidor antigo que ainda esteja na porta 8170
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":8170 .*LISTENING"') do taskkill /PID %%p /F >nul 2>nul
start "" /min cmd /c "timeout /t 2 >nul & start http://localhost:8170/telao & start http://localhost:8170/qr"
%PY% server.py
pause
