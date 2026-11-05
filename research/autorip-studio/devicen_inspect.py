"""Inspeção estática (NUNCA avaliação) de declarações /DeviceN em texto.

O texto contém nomes lógicos anunciados por uma configuração do FlexiPRINT.
Não é RIP e não estabelece o significado dos bytes PRT ou canais Hoson.
"""
import hashlib
import json
import re
from pathlib import Path

MAX_CONFIG_BYTES = 64 * 1024
_DEVICE_N = re.compile(rb'/DeviceN\s*\{([^{}]*)\}', re.ASCII)
_NAME = re.compile(rb'/([A-Za-z_$][A-Za-z_0-9$]*)', re.ASCII)


class DeviceNError(ValueError):
    pass


def inspect_devicen_text(path, *, max_bytes=MAX_CONFIG_BYTES):
    p = Path(path)
    with p.open('rb') as f:
        before = p.stat()
        if not 1 <= before.st_size <= min(MAX_CONFIG_BYTES,max_bytes):
            raise DeviceNError('Configuration text exceeds safe size limit or is empty')
        raw = f.read(MAX_CONFIG_BYTES + 1)
        after = p.stat()
    if len(raw) != before.st_size or (before.st_size,before.st_mtime_ns,before.st_ino) != (after.st_size,after.st_mtime_ns,after.st_ino):
        raise DeviceNError('Configuration text changed during inspection')
    match = _DEVICE_N.search(raw)
    if not match:
        raise DeviceNError('No simple DeviceN declaration found')
    names = [m.decode('ascii') for m in _NAME.findall(match.group(1))]
    if not names or len(names) > 64:
        raise DeviceNError('Invalid or empty DeviceN names')
    return {'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes':len(raw),'declared_names':names,'declared_count':len(names),
            'candidate_spots':[x for x in names if x.startswith('Spot_')],
            'raster_mapping':'unverified',
            'warning':'DeviceN names in text are not proof of white ink, PRT raster layout, or ICC suitability.'}


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(description='Read-only DeviceN metadata parser')
    p.add_argument('path');args=p.parse_args()
    print(json.dumps(inspect_devicen_text(args.path),indent=2))
