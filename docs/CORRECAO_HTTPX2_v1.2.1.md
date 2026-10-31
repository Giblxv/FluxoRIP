# Correção do erro Starlette TestClient / httpx2

O erro surge durante `python -m unittest discover -s tests -v` por falta de dependência opcional usada por `starlette.testclient`, importada de `fastapi.testclient`.

A biblioteca `httpx2` foi incluída em `requirements-build.txt` para que `GERAR_EXECUTAVEL.bat` a instale antes dos testes.

## Correção manual sem reinstalar

```powershell
cd C:\Users\arauj\Downloads\FORGE_v1.2_Central_Multiestacoes
.\.venv-build\Scripts\python.exe -m pip install "httpx2>=2.13,<3"
.\.venv-build\Scripts\python.exe -m unittest discover -s tests -v
```

`httpx2` é usado no teste e não precisa ser instalado manualmente no Windows onde o EXE final será executado. O aplicativo continua sem enviar comandos diretos à placa Hoson.

Fontes:
- https://www.starlette.io/testclient/
- https://pypi.org/project/httpx2/
