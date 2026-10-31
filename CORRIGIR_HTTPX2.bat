@echo off
setlocal
cd /d "%~dp0"
title Fluxo RIP - Corrigir dependencias de testes
if not exist ".venv-build\Scripts\python.exe" (
 echo Ambiente .venv-build nao encontrado. Execute GERAR_EXECUTAVEL.bat primeiro.
 pause
 exit /b 1
)
echo Instalando httpx2 no ambiente de compilacao...
".venv-build\Scripts\python.exe" -m pip install "httpx2>=2.13,<3"
if errorlevel 1 goto ERRO
echo.
echo Executando testes...
".venv-build\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto ERRO
echo.
echo Testes aprovados. Agora execute GERAR_EXECUTAVEL.bat.
pause
exit /b 0
:ERRO
echo.
echo Erro. Envie a saida completa para diagnostico.
pause
exit /b 1
