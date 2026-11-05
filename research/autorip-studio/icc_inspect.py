"""Read-only ICC header/tag-directory inspector; does not apply color transforms."""
import hashlib
import json
import struct
from pathlib import Path

MAX_ICC_BYTES = 64 * 1024 * 1024

class ICCError(ValueError):
    pass

def inspect_icc(path, *, max_bytes=MAX_ICC_BYTES):
    p = Path(path)
    with p.open('rb') as f:
        st = p.stat()
        if st.st_size < 132 or st.st_size > max_bytes:
            raise ICCError('ICC size outside limits')
        raw = f.read()
        if len(raw) != st.st_size:
            raise ICCError('ICC truncated during read')
        after = p.stat()
        if (st.st_size, st.st_mtime_ns, st.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ICCError('ICC changed during read')
    declared = struct.unpack_from('>I', raw, 0)[0]
    if declared != len(raw):
        raise ICCError('ICC declared size mismatch')
    if raw[36:40] != b'acsp':
        raise ICCError('ICC acsp signature absent')
    tag_count = struct.unpack_from('>I', raw, 128)[0]
    if tag_count > (len(raw)-132)//12:
        raise ICCError('ICC tag directory truncated')
    tags = []
    for i in range(tag_count):
        pos = 132 + i*12
        sig = raw[pos:pos+4].decode('latin-1')
        off, size = struct.unpack_from('>II', raw, pos+4)
        if off < 128 or size > len(raw) or off > len(raw)-size:
            raise ICCError('ICC tag points outside file')
        tags.append({'signature': sig, 'offset': off, 'size': size})
    cs = raw[16:20].decode('latin-1')
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
            'profile_class': raw[12:16].decode('latin-1'),
            'device_color_space': cs, 'pcs': raw[20:24].decode('latin-1'),
            'icc_version_major': raw[8], 'tags': tags,
            'channel_count_candidate': {'GRAY':1, 'RGB ':3, 'CMYK':4}.get(cs, int(cs[0],16) if len(cs)==4 and cs[1:]=='CLR' and cs[0] in '23456789ABCDEF' else None),
            'warning': 'Header metadata only; does not prove DTF ink ordering, white channel or print suitability.'}

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    args = ap.parse_args()
    print(json.dumps(inspect_icc(args.path), indent=2))
