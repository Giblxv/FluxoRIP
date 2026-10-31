"""Autenticação do modo Central; não habilitada no modo localhost.

A interface usa HTTP Basic apenas na rede local isolada. Para qualquer rede
compartilhada ou acesso externo, coloque HTTPS/TLS via proxy seguro/VPN.
O token separado de agente permite somente enviar dados de observação.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from fastapi import Request
from fastapi.responses import JSONResponse
from app.paths import DATA_ROOT

CREDENTIAL_FILE = DATA_ROOT / 'central_auth.json'
ITERATIONS = 350_000


def create_credentials(force=False):
    if CREDENTIAL_FILE.exists() and not force:
        raise FileExistsError('Central ja configurada. Use --redefinir-central para trocar a senha.')
    password = secrets.token_urlsafe(25)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITERATIONS)
    payload = {'username':'forge', 'iterations':ITERATIONS, 'salt':base64.b64encode(salt).decode(),
               'hash':base64.b64encode(digest).decode(), 'agent_token':secrets.token_urlsafe(42),
               'created_at': datetime.now(timezone.utc).isoformat()}
    CREDENTIAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = CREDENTIAL_FILE.with_suffix('.tmp')
    temp.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    os.replace(temp, CREDENTIAL_FILE)
    try: os.chmod(CREDENTIAL_FILE, 0o600)
    except OSError: pass
    return password


def get_credentials():
    if not CREDENTIAL_FILE.is_file():
        raise RuntimeError('Antes de iniciar Central, execute FluxoRIP.exe --configurar-central')
    return json.loads(CREDENTIAL_FILE.read_text(encoding='utf-8'))


def verify_admin(authorization, config):
    if not authorization or not authorization.startswith('Basic '): return False
    try:
        raw = base64.b64decode(authorization[6:], validate=True).decode('utf-8')
        user, sep, passwd = raw.partition(':')
        if not sep or not secrets.compare_digest(user, config['username']): return False
        salt = base64.b64decode(config['salt'])
        correct = base64.b64decode(config['hash'])
        actual = hashlib.pbkdf2_hmac('sha256', passwd.encode(), salt, int(config['iterations']))
        return hmac.compare_digest(actual, correct)
    except (ValueError, UnicodeError, KeyError, TypeError):
        return False


def verify_agent(token, config):
    return bool(token) and secrets.compare_digest(token, config.get('agent_token', ''))


async def auth_middleware(request: Request, call_next):
    if os.environ.get('FORGE_CENTRAL_MODE') != '1':
        return await call_next(request)
    try:
        config = get_credentials()
    except Exception:
        return JSONResponse({'detail':'Central nao configurada'}, status_code=503)
    path = request.url.path
    agent_path = path == '/api/stations/heartbeat'
    if agent_path:
        allowed = verify_agent(request.headers.get('x-forge-agent-key',''), config)
    else:
        allowed = verify_admin(request.headers.get('authorization',''), config)
    if not allowed:
        headers = {} if agent_path else {'WWW-Authenticate':'Basic realm="Fluxo RIP Central"'}
        return JSONResponse({'detail':'Autenticacao necessaria'},status_code=401,headers=headers)
    # Reject cross-origin browser writes in central mode, even if Basic credentials
    # happen to be cached by the browser. Agent requests have no Origin header.
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        if origin:
            expected=f'{request.url.scheme}://{request.headers.get("host", "")}'
            if origin.rstrip('/') != expected.rstrip('/'):
                return JSONResponse({'detail':'Origem nao autorizada'},status_code=403)
    response=await call_next(request)
    response.headers['X-Frame-Options']='DENY'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response
