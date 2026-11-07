@echo off
setlocal
title Fluxo RIP - Preparar caminho de arquivo
echo Aguarde a impressao terminar normalmente antes do ensaio.
echo Deixe a janela Abrir arquivo do PrintExp aberta com o campo de nome vazio.
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Preparar-Caminho.ps1" -Prepare
pause
