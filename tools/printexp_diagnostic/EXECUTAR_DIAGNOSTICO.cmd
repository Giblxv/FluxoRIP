@echo off
setlocal
title Fluxo RIP - Diagnostico de leitura v3
echo Abra o PrintExp e o Production Manager antes de continuar.
echo Aguarde a impressao atual terminar normalmente antes desta coleta.
echo Este diagnostico nao envia trabalhos nem comandos para a impressora.
echo Para investigar importacao, deixe a janela OpenFiles do PrintExp aberta sem selecionar arquivo.
echo.
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Diagnosticar-PrintExp.ps1"
set "FLUXO_DIAG_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %FLUXO_DIAG_EXIT%
