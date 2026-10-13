@echo off
REM Rode com botao direito > Executar como administrador (uma vez so)
netsh advfirewall firewall delete rule name="Ze Express Churrasco 8170" >nul 2>nul
netsh advfirewall firewall add rule name="Ze Express Churrasco 8170" dir=in action=allow protocol=TCP localport=8170 profile=any
echo.
echo Porta 8170 liberada no firewall do Windows.
pause
