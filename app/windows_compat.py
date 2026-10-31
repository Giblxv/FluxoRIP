"""Compatibilidade sem alterações no sistema para Windows 10 e Windows 11.

Esta camada nunca modifica IPs, chaves do registro, firewall ou placas de rede.
"""
from __future__ import annotations

import platform
import subprocess
import sys
from typing import Any

# Identificador público do Edge WebView2 Evergreen Runtime no registro do Windows.
WEBVIEW2_CLIENT_GUID = '{F1E7A0B6-3F61-4F58-AF5F-68C0E42C57A6}'


def windows_details() -> dict[str, Any]:
    if sys.platform != 'win32':
        return {'platform': sys.platform, 'windows': False, 'supported': False,
                'name': platform.system(), 'build': None, 'arch': platform.machine()}
    info = sys.getwindowsversion()
    build = int(info.build)
    # Both Windows 10 and 11 report NT 10.0; distinguish using build number.
    # Windows Server builds can share NT 10.0 and must not be labeled as client.
    is_server = int(getattr(info, 'product_type', 1)) != 1
    name = 'Windows Server' if is_server else ('Windows 11' if build >= 22000 else 'Windows 10')
    supported = int(info.major) == 10 and build >= 17763
    return {'platform': sys.platform, 'windows': True, 'supported': supported,
            'name': name, 'build': build, 'arch': platform.machine(),
            'version': f'{info.major}.{info.minor}.{build}'}


def webview2_runtime() -> dict[str, Any]:
    """Best effort detection; registry-only probe does not install anything.

    Returns detected=None when the registry cannot be checked. The GUI startup
    also traps pywebview failures and offers browser mode.
    """
    if sys.platform != 'win32':
        return {'detected': None, 'version': None, 'reason': 'Consulta disponível no Windows'}
    try:
        import winreg
    except ImportError:
        return {'detected': None, 'version': None, 'reason': 'Registro indisponível'}
    path = r'SOFTWARE\Microsoft\EdgeUpdate\Clients' + '\\' + WEBVIEW2_CLIENT_GUID
    hives = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]
    views = [0, getattr(winreg, 'KEY_WOW64_32KEY', 0), getattr(winreg, 'KEY_WOW64_64KEY', 0)]
    for hive in hives:
        for view in dict.fromkeys(views):
            try:
                with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | view) as key:
                    version = str(winreg.QueryValueEx(key, 'pv')[0]).strip()
                    if version and version != '0.0.0.0':
                        return {'detected': True, 'version': version, 'reason': 'WebView2 registrado'}
            except (OSError, ValueError):
                continue
    return {'detected': False, 'version': None,
            'reason': 'WebView2 não identificado no registro; a janela pode falhar'}


def powershell_status() -> dict[str, Any]:
    """Read-only query used by --diagnostico; no network probes executed."""
    if sys.platform != 'win32':
        return {'available': False, 'version': None, 'network_cmdlets': False}
    code = ('$PSVersionTable.PSVersion.ToString() + "|" + '
            '([bool](Get-Command Get-NetAdapter -ErrorAction SilentlyContinue)).ToString() + "|" + '
            '([bool](Get-Command Get-NetNeighbor -ErrorAction SilentlyContinue)).ToString()')
    try:
        proc = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', code],
                              capture_output=True, timeout=8,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if proc.returncode:
            return {'available': False, 'version': None, 'network_cmdlets': False}
        fields = proc.stdout.decode('utf-8-sig', errors='replace').strip().split('|')
        return {'available': True, 'version': fields[0],
                'network_cmdlets': len(fields) >= 3 and fields[1].lower() == 'true' and fields[2].lower() == 'true'}
    except (OSError, subprocess.TimeoutExpired):
        return {'available': False, 'version': None, 'network_cmdlets': False}


def compatibility_report() -> dict[str, Any]:
    info = windows_details()
    view = webview2_runtime()
    return {'os': info, 'webview2': view, 'powershell': powershell_status(),
            'recommended': 'Windows 10 22H2 x64 ou Windows 11 x64; Edge WebView2 Runtime',
            'mode': 'Local e passivo; não altera a rede ou as impressoras'}
