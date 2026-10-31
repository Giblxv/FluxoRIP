@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CONFIGURAR_ESTACAO.ps1"
pause
