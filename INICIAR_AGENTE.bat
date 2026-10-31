@echo off
cd /d "%~dp0"
if not exist "dist\FluxoRIP.exe" (echo Execute GERAR_EXECUTAVEL.bat primeiro.& pause& exit /b 1)
echo O agente nao envia comandos ao PrintExp.
echo Ele envia informacoes da estacao a cada 120 segundos.
echo Use o Gerenciador de Tarefas para encerrar se necessario.
start "Fluxo RIP Agente" "dist\FluxoRIP.exe" --agente
