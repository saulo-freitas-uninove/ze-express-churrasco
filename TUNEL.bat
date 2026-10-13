@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist cloudflared.exe (
  echo Baixe o cloudflared.exe e coloque nesta pasta. Veja LEIA-ME_ONLINE.txt
  pause
  exit /b 1
)
echo Aguarde: o link https://....trycloudflare.com vai aparecer abaixo. Use esse link no celular.
cloudflared.exe tunnel --url http://localhost:8170
pause
