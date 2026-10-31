@echo off
cd /d "%~dp0"
if not exist "dist\FluxoRIP.exe" (
 echo Primeiro execute INSTALAR_E_ABRIR.bat
 pause
 exit /b 1
)
"dist\FluxoRIP.exe" --assistente
