"""Separate read-only PyInstaller resources from persistent production data."""
import os
import sys
from pathlib import Path

# One-file executable extracts read-only resources to a temporary directory.
BUNDLE_ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))

def get_data_root() -> Path:
    custom = os.environ.get('FORGE_DATA_DIR')
    if custom:
        path = Path(custom).expanduser().resolve()
    elif getattr(sys, 'frozen', False):
        local = os.environ.get('LOCALAPPDATA')
        path = (Path(local) if local else Path.home() / 'AppData' / 'Local') / 'FORGE'
    else:
        # Running from source preserves the v0.6 development directory layout.
        path = Path(__file__).resolve().parent.parent
    path.mkdir(parents=True, exist_ok=True)
    return path

DATA_ROOT = get_data_root()
