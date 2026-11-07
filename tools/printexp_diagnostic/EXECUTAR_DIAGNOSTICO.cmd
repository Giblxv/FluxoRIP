@echo off
setlocal
title Fluxo RIP - Diagnostico de leitura
echo Abra o PrintExp e o Production Manager antes de continuar.
echo Este diagnostico nao envia trabalhos nem comandos para a impressora.
echo.
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Diagnosticar-PrintExp.ps1"
set "FLUXO_DIAG_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %FLUXO_DIAG_EXIT%
