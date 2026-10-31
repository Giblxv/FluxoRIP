@echo off
setlocal
cd /d "%~dp0"
title Fluxo RIP - Central de Producao (Windows 10/11)
if not exist "dist\FluxoRIP.exe" (
 echo Nao encontrado: dist\FluxoRIP.exe. Execute GERAR_EXECUTAVEL.bat.
 pause
 exit /b 1
)
echo Informe o IP da REDE ADMINISTRATIVA deste computador.
echo Nao use IP da placa isolada Hoson 192.168.127.x.
echo Exemplo: 192.168.1.100
echo.
set /p "CENTRAL_HOST=IPv4 local da Central: "
if not defined CENTRAL_HOST exit /b 1
"dist\FluxoRIP.exe" --central --host "%CENTRAL_HOST%" --port 8765
if errorlevel 1 (
 echo Falha ao iniciar. Confira o arquivo forge.log em %%LOCALAPPDATA%%\FORGE.
 pause
)
