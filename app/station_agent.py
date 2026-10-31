"""Agente de estação: envia somente observações locais para a Central.

Nunca recebe ou executa comandos remotos nem altera impressoras, PrintExp,
placas de rede, gateways ou firewall. Scan IPv4 só mediante consentimento
expresso no arquivo estacao.json (scan_on_start=true).
"""
from __future__ import annotations
import json
import logging
import os
import platform
import socket
import time
import uuid
import ipaddress
from pathlib import Path
from urllib import request, error, parse
from app.paths import DATA_ROOT
from app.network_scanner import get_adapters, scan_network, ScanRequest

CONFIG_PATH = DATA_ROOT / 'estacao.json'
ID_PATH = DATA_ROOT / 'estacao_id.txt'


def local_station_id():
    if not ID_PATH.exists():
        ID_PATH.write_text('st-'+uuid.uuid4().hex,encoding='utf-8')
    return ID_PATH.read_text(encoding='utf-8').strip()


def read_config():
    if not CONFIG_PATH.is_file():
        raise RuntimeError('Configure a estacao: veja docs/CENTRAL_E_ESTACOES.md e estacao.exemplo.json')
    cfg=json.loads(CONFIG_PATH.read_text(encoding='utf-8-sig'))
    url=str(cfg.get('central_url','')).rstrip('/')
    parsed=parse.urlsplit(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError('central_url deve ser somente http(s)://IP:PORTA (sem caminho ou credenciais)')
    # Do not allow automatic token exfiltration to public servers.
    try:
        addr=ipaddress.ip_address(parsed.hostname)
        if not (addr.is_private or addr.is_loopback): raise ValueError('Central deve estar em um IP privado')
    except ValueError as exc:
        raise ValueError('Use IP numerico privado na central_url') from exc
    token=str(cfg.get('agent_token',''))
    if len(token)<24:raise ValueError('agent_token invalido ou ausente')
    return {'central_url':url,'agent_token':token,
            'station_name':str(cfg.get('station_name') or socket.gethostname())[:120],
            'scan_on_start':cfg.get('scan_on_start') is True}


def build_heartbeat(name, do_scan=False):
    try:
        adapters=get_adapters()
    except Exception as exc:
        logging.warning('Consulta de adaptadores indisponivel: %s',exc)
        adapters=[]
    interfaces=[]
    observations=[]
    for adapter in adapters[:32]:
        ips=[str(a.get('ip')) for a in adapter.get('ips',[])][:16]
        interfaces.append({'id':int(adapter['id']),'name':str(adapter['name'])[:120],
            'status':str(adapter.get('status',''))[:30], 'ips':ips,
            'hoson_subnet':bool(adapter.get('is_hoson_subnet'))})
        if do_scan and adapter.get('is_hoson_subnet') and str(adapter.get('status','')).lower()=='up':
            try:
                report=scan_network(ScanRequest(interface_index=int(adapter['id'])), adapters=adapters)
                for device in report.get('devices',[]):
                    observations.append({'ip':str(device['ip']), 'mac':device.get('mac'),
                        'interface_name':str(adapter['name'])[:120], 'interface_id':int(adapter['id']), 'evidence':device.get('evidence',[])})
            except Exception as exc:
                logging.warning('Scanner de %s nao completou: %s',adapter.get('name'),exc)
    return {'station_id':local_station_id(),'station_name':name,'hostname':socket.gethostname()[:120],
        'os_name':platform.platform()[:70], 'interfaces':interfaces,'observations':observations[:256]}


def send_heartbeat(cfg,payload):
    body=json.dumps(payload).encode('utf-8')
    url=cfg['central_url']+'/api/stations/heartbeat'
    req=request.Request(url,body,headers={'Content-Type':'application/json',
        'X-FORGE-Agent-Key':cfg['agent_token']},method='POST')
    # No HTTP redirects: never forward the agent key to a different host.
    class NoRedirect(request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=request.build_opener(NoRedirect)
    with opener.open(req,timeout=12) as r:
        result=json.loads(r.read(50000).decode('utf-8'))
        if not result.get('received'):
            raise RuntimeError('Central nao confirmou recebimento')
    return result


def run_agent_once(cfg=None):
    cfg=cfg or read_config()
    return send_heartbeat(cfg,build_heartbeat(cfg['station_name'],do_scan=cfg['scan_on_start']))


def run_agent():
    cfg=read_config()
    first=True
    while True:
        try:
            send_heartbeat(cfg,build_heartbeat(cfg['station_name'],do_scan=first and cfg['scan_on_start']))
            logging.info('Estacao informada a Central %s',cfg['central_url'])
        except Exception:
            logging.exception('Falha no heartbeat; tentara novamente')
        first=False
        time.sleep(120)
