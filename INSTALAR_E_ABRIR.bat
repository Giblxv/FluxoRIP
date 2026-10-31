@echo off
setlocal
cd /d "%~dp0"
title Fluxo RIP - Instalacao em um clique
if exist "dist\FluxoRIP.exe" goto ABRIR

echo =====================================================
echo  FLUXO RIP - INSTALACAO SIMPLIFICADA

echo  Gerando o executavel pela primeira vez...
echo  O processo requer Python 3.12 x64 e internet.
echo  Nada sera alterado nas impressoras ou IPs.
echo =====================================================
echo.
call "GERAR_EXECUTAVEL.bat" --automatico
if errorlevel 1 goto ERRO
:ABRIR
if not exist "dist\FluxoRIP.exe" goto ERRO
echo Iniciando Fluxo RIP...
start "" "dist\FluxoRIP.exe"
exit /b 0
:ERRO
echo.
echo NAO FOI POSSIVEL CONCLUIR.
echo Envie uma foto desta janela ou o arquivo de log para diagnostico.
pause
exit /b 1
