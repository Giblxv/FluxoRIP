@echo off
setlocal
cd /d "%~dp0"
title Fluxo RIP 1.5 - Windows 10 e Windows 11
set "NO_PAUSE=0"
if /I "%~1"=="--automatico" set "NO_PAUSE=1"

echo ==============================================
echo   FLUXO RIP 1.5 - COMPILAR PARA WINDOWS 10/11 X64
echo ==============================================
echo.
where py >nul 2>&1
if errorlevel 1 (
  echo ERRO: Python Launcher ausente. Instale Python 3.12 64 bits.
  goto ERROR
)
py -3.12 -c "import struct,sys; assert struct.calcsize('P')==8, 'Python precisa ser 64 bits'; print(sys.version)"
if errorlevel 1 goto ERROR
if not exist ".venv-build\Scripts\python.exe" (
  py -3.12 -m venv ".venv-build"
  if errorlevel 1 goto ERROR
)
".venv-build\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto ERROR
".venv-build\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto ERROR
".venv-build\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto ERROR
".venv-build\Scripts\python.exe" -m PyInstaller --clean --noconfirm FORGE.spec
if errorlevel 1 goto ERROR
set FORGE_NO_DIALOG=1
"dist\FluxoRIP.exe" --autoteste
if errorlevel 1 goto ERROR
set FORGE_NO_DIALOG=
echo.
echo COMPILACAO E AUTOTESTE CONCLUIDOS.
echo Arquivo: dist\FluxoRIP.exe
echo Copie este unico arquivo para o Windows 10/11 x64.
echo A maquina de destino deve ter WebView2 para janela nativa.
echo Se nao tiver, o Fluxo RIP tenta abrir no navegador.
if "%NO_PAUSE%"=="0" pause
exit /b 0
:ERROR
echo.
echo Falha durante instalacao, testes ou compilacao.
echo Confira a mensagem anterior. Dados anteriores nao foram apagados.
if "%NO_PAUSE%"=="0" pause
exit /b 1
