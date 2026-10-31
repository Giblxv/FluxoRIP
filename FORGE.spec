# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH)
hiddenimports = ['clr', 'vtracer'] + collect_submodules('uvicorn')
a = Analysis(
    ['forge_launcher.py'],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'web'), 'web'), (str(root / 'setup' / 'ASSISTENTE_FORGE.ps1'), 'setup')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PyQt6', 'PySide6'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FluxoRIP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(root / "FluxoRIP.ico"),
    disable_windowed_traceback=False,
)
