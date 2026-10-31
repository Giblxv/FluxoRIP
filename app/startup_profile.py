"""Persisted, non-secret setup mode for FORGE's first-run wizard."""
import ipaddress
import json
from pathlib import Path
from app.paths import DATA_ROOT

PROFILE_PATH = DATA_ROOT / 'modo_inicial.json'


def validate_profile(raw: object) -> dict:
    if not isinstance(raw, dict):
        raise ValueError('Configuração inicial inválida.')
    mode = raw.get('modo')
    if mode == 'local':
        return {'modo': 'local'}
    if mode == 'estacao':
        return {'modo': 'estacao'}
    if mode != 'central':
        raise ValueError('Escolha o modo local, central ou estacao no assistente.')
    try:
        ip = ipaddress.ip_address(str(raw['ip']))
        port = int(raw.get('porta', 8765))
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError('O IP e a porta da Central são obrigatórios.') from exc
    if (ip.version != 4 or not ip.is_private or ip.is_loopback or
            ip.is_link_local or ip.is_multicast or ip.is_unspecified or
            ip in ipaddress.ip_network('192.168.127.0/24')):
        raise ValueError('Use o IPv4 privado da rede administrativa, não o da Hoson.')
    if not 1024 <= port <= 65535:
        raise ValueError('A porta da Central deve estar entre 1024 e 65535.')
    return {'modo': 'central', 'ip': str(ip), 'porta': port}


def load_profile(path: Path | None = None) -> dict | None:
    file = path or PROFILE_PATH
    if not file.is_file():
        return None
    return validate_profile(json.loads(file.read_text(encoding='utf-8-sig')))
