@echo off
cd /d "%~dp0"
if not exist "dist\FluxoRIP.exe" (echo Execute GERAR_EXECUTAVEL.bat primeiro.& pause& exit /b 1)
"dist\FluxoRIP.exe" --configurar-central
