"""Safe, local IPv4 inventory for printer workstations on Windows 10/11.

Only selected local Ethernet-connected subnets; low-rate ICMP echo and OS ARP cache.
No TCP printer commands, SNMP writes, broadcast traffic or automatic NIC edits.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import ipaddress
import json
import os
import re
import subprocess
import sys
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix='/api/network', tags=['Scanner de rede'])

# Bound scan resources so a mistaken click doesn't sweep a large network.
MAX_HOSTS = 254
MAX_WORKERS = 12
PING_TIMEOUT_MS = 650

class ScanRequest(BaseModel):
    interface_index: int = Field(ge=1)
    network: str = Field(default='192.168.127.0/24', max_length=32)


def _run_powershell(code: str, timeout: float = 12) -> Any:
    if sys.platform != 'win32':
        return []
    # Script is always built from constants or validated integer ifIndex, not user text.
    script = '[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); ' + code
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                                capture_output=True, timeout=timeout, creationflags=flags)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f'Não foi possível consultar o PowerShell: {exc}') from exc
    if result.returncode != 0:
        message = result.stderr.decode('utf-8', errors='replace').strip()
        raise RuntimeError('Consulta de rede falhou: ' + message[:350])
    raw = result.stdout.decode('utf-8-sig', errors='replace').strip()
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError('Resposta de rede do Windows inválida') from exc


def get_adapters() -> list[dict]:
    """Windows Get-NetAdapter & Get-NetIPAddress. Includes unplugged Ethernet NICs."""
    result = _run_powershell(r'''
        $result = @(
          Get-NetAdapter -ErrorAction Stop | ForEach-Object {
            $a = $_
            $ips = @(
              Get-NetIPAddress -InterfaceIndex $a.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
              Where-Object { $_.IPAddress -ne '0.0.0.0' } |
              ForEach-Object { @{ ip = [string]$_.IPAddress; prefix = [int]$_.PrefixLength } }
            )
            [pscustomobject]@{
              id = [int]$a.ifIndex
              name = [string]$a.Name
              description = [string]$a.InterfaceDescription
              mac = [string]$a.MacAddress
              status = [string]$a.Status
              link_speed = [string]$a.LinkSpeed
              ips = $ips
            }
          }
        )
        ConvertTo-Json -InputObject $result -Compress -Depth 7
    ''')
    if not isinstance(result, list):
        result = [result] if isinstance(result, dict) else []
    output = []
    for entry in result:
        if not isinstance(entry, dict):
            continue
        try:
            entry['id'] = int(entry['id'])
            entry['ips'] = [
                {'ip': str(ipaddress.IPv4Address(p['ip'])), 'prefix': int(p['prefix'])}
                for p in (entry.get('ips') or [])
                if 0 <= int(p['prefix']) <= 32
            ]
            entry['is_hoson_subnet'] = any(ipaddress.IPv4Address(p['ip']) in ipaddress.IPv4Network('192.168.127.0/24') for p in entry['ips'])
            output.append(entry)
        except (ValueError, KeyError, TypeError, ipaddress.AddressValueError):
            continue
    return sorted(output, key=lambda item: (not item['is_hoson_subnet'], item['name'].lower()))


def get_neighbors(interface_index: int) -> dict[str, dict]:
    """Read the existing IPv4 neighbor cache for the *selected* interface."""
    if sys.platform != 'win32':
        return {}
    entries = _run_powershell(r'''
        $result = @(
          Get-NetNeighbor -AddressFamily IPv4 -InterfaceIndex %d -ErrorAction SilentlyContinue |
          ForEach-Object { [pscustomobject]@{
            ip = [string]$_.IPAddress
            mac = [string]$_.LinkLayerAddress
            state = [string]$_.State
          } }
        )
        ConvertTo-Json -InputObject $result -Compress -Depth 5
    ''' % int(interface_index))
    if not isinstance(entries, list):
        entries = [entries] if isinstance(entries, dict) else []
    return {e['ip']: e for e in entries if isinstance(e, dict) and 'ip' in e}


def ping_target(target: str, source: str) -> bool:
    """Single ICMP echo only, explicitly declaring a source IPv4 address."""
    if sys.platform != 'win32':
        return False
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    try:
        result = subprocess.run(['ping.exe', '-4', '-n', '1', '-w', str(PING_TIMEOUT_MS), '-S', source, target],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=2.3, creationflags=flags)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def scan_network(request: ScanRequest, adapters: list[dict] | None = None) -> dict:
    adapters = get_adapters() if adapters is None else adapters
    adapter = next((a for a in adapters if int(a['id']) == request.interface_index), None)
    if not adapter:
        raise ValueError('Adaptador de rede não encontrado. Atualize a lista de interfaces.')
    if str(adapter.get('status', '')).lower() != 'up':
        raise ValueError('A placa de rede selecionada está desconectada (status diferente de Up).')
    try:
        network = ipaddress.ip_network(request.network, strict=True)
    except ValueError as exc:
        raise ValueError('Informe uma rede IPv4 válida, por exemplo 192.168.127.0/24.') from exc
    if network.version != 4 or network.num_addresses - 2 > MAX_HOSTS or network.prefixlen != 24:
        raise ValueError('A versão atual permite apenas uma rede IPv4 /24 por vez (até 254 endereços).')
    if not network.is_private:
        raise ValueError('Por segurança, apenas redes IPv4 privadas podem ser verificadas.')
    # Safety and correctness: probe only a directly attached subnet.
    attached = []
    for item in adapter.get('ips', []):
        try:
            local_ip = ipaddress.IPv4Address(item['ip'])
            local_net = ipaddress.IPv4Network((item['ip'], int(item['prefix'])), strict=False)
            if network.subnet_of(local_net) and local_ip in network:
                attached.append((local_ip, local_net))
        except (ValueError, KeyError, TypeError):
            continue
    if not attached:
        raise ValueError('O adaptador não possui um IP na sub-rede selecionada. Confira IPv4 e máscara no Windows; o Fluxo RIP não altera essa configuração.')
    source = str(attached[0][0])
    local_ips = {p['ip'] for p in adapter.get('ips', [])}
    hosts = [str(host) for host in network.hosts() if str(host) not in local_ips]
    scanned_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    replies = set()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(ping_target, ip, source): ip for ip in hosts}
        for future in as_completed(futures):
            try:
                if future.result():
                    replies.add(futures[future])
            except Exception:
                pass
    # ARP helps discover local devices that don't respond to ICMP; stale entries
    # are reported as unconfirmed rather than a connected printer.
    neighbor_error = None
    try:
        neighbors = get_neighbors(request.interface_index)
    except RuntimeError as exc:
        neighbors = {}
        neighbor_error = str(exc)
    results = []
    for ip in sorted(set(replies) | set(neighbors), key=lambda x: tuple(int(z) for z in x.split('.')) if re.fullmatch(r'\d+\.\d+\.\d+\.\d+', x) else (999,)):
        try:
            addr = ipaddress.IPv4Address(ip)
        except ipaddress.AddressValueError:
            continue
        if addr not in network or ip in local_ips:
            continue
        neigh = neighbors.get(ip) or {}
        mac = str(neigh.get('mac') or '').strip()
        neighbor_state = str(neigh.get('state') or '')
        # Ignore multicast/broadcast/empty neighbors; ARP cache can be stale.
        usable_mac = bool(re.fullmatch(r'(?i)(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}', mac)) and mac.lower() not in ('00-00-00-00-00-00', 'ff-ff-ff-ff-ff-ff')
        icmp = ip in replies
        arp_recent = usable_mac and neighbor_state.lower() in ('reachable', 'delay', 'probe', 'permanent')
        if not (icmp or arp_recent):
            continue
        results.append({
            'ip': ip,
            'mac': mac if usable_mac else None,
            'icmp': icmp,
            'arp_state': neighbor_state or None,
            'evidence': ['ICMP'] * int(icmp) + (['ARP'] if arp_recent else []),
            'possible_hoson': ip in ('192.168.127.10', '192.168.127.1'),
            'device_type': 'não identificado',
            'status': 'respondeu' if icmp else 'detectado na vizinhança ARP',
        })
    return {
        'interface': {'id': adapter['id'], 'name': adapter['name'], 'ip': source, 'mac': adapter.get('mac'), 'link_speed': adapter.get('link_speed')},
        'network': str(network), 'scanned': len(hosts), 'found': len(results), 'devices': results,
        'started_at': scanned_at, 'elapsed_s': round(time.monotonic() - started, 2),
        'method': 'ICMP + cache ARP (somente leitura)',
        'warning': 'Dispositivo encontrado não significa impressora Hoson confirmada. Alguns dispositivos bloqueiam ping; uma placa com IP repetido em outra interface pode não ser identificada corretamente.',
        'neighbor_error': neighbor_error,
        'commands_sent_to_printer': False,
        'network_configuration_changed': False,
    }


@router.get('/interfaces')
def interfaces():
    try:
        return {'platform': sys.platform, 'adapters': get_adapters(),
                'hint': 'Escolha a porta Ethernet ligada à impressora. No caso típico Hoson, use a rede 192.168.127.0/24.'}
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post('/scan')
def scan(payload: ScanRequest):
    if sys.platform != 'win32':
        raise HTTPException(501, 'O scanner de interfaces físicas requer Windows 10 ou 11.')
    try:
        return scan_network(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

@router.post('/scan-all')
def scan_all_hoson_ports():
    """Scan all connected NICs configured on the Hoson reference network.

    Results preserve the interface index; equal IPs on different dedicated
    adapters are separate observations. Windows routing can nevertheless make
    a same-subnet multi-adapter setup ambiguous.
    """
    if sys.platform != 'win32':
        raise HTTPException(501, 'O scanner de interfaces físicas requer Windows 10 ou 11.')
    try:
        adapters = get_adapters()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    candidates = [a for a in adapters if a.get('is_hoson_subnet') and str(a.get('status', '')).lower() == 'up'
                  and any(ipaddress.IPv4Address(p['ip']) in ipaddress.IPv4Network('192.168.127.0/24')
                          for p in a.get('ips', []))]
    if not candidates:
        raise HTTPException(422, 'Nenhuma placa conectada e configurada em 192.168.127.x foi encontrada. Escolha outra faixa manualmente ou confira o IPv4.')
    reports = []
    errors = []
    # At most two NICs scanning simultaneously to avoid overloading a station.
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(scan_network, ScanRequest(interface_index=a['id']), adapters): a for a in candidates}
        for task in as_completed(futures):
            adapter = futures[task]
            try:
                report = task.result()
                reports.append(report)
            except Exception as exc:
                errors.append({'interface': adapter['name'], 'message': str(exc)[:250]})
    reports.sort(key=lambda r: r['interface']['id'])
    devices = []
    for r in reports:
        for item in r['devices']:
            devices.append({**item, 'interface_id': r['interface']['id'], 'interface_name': r['interface']['name']})
    return {
        'network': '192.168.127.0/24',
        'scanned': sum(r['scanned'] for r in reports),
        'found': len(devices),
        'devices': devices,
        'interfaces_scanned': len(reports),
        'elapsed_s': round(max([r['elapsed_s'] for r in reports], default=0),2),
        'errors': errors,
        'warning': 'Observações por placa Ethernet; não garantem identificação da Hoson nem isolamento físico se há IPs duplicados na mesma sub-rede. Conexões sem IPv4 192.168.127.x não foram verificadas.',
        'commands_sent_to_printer': False,
        'network_configuration_changed': False,
    }
