"""Read-only structural hypothesis checker; never interprets channels as ink."""
import argparse, hashlib, json, os, struct
from pathlib import Path

HEADER=48
MAX_INPUT_BYTES = 8 * 1024**3
MAX_ROWS = 10_000_000
MAX_STRIDE = 1_000_000
MAX_SLOTS = 64

def inspect(path, *, max_bytes=None):
    path=Path(path)
    with path.open('rb') as f:
        h=f.read(HEADER)
        if len(h)!=HEADER: raise ValueError('truncated header')
        fields=struct.unpack('<12I',h)
        if fields[0]!=0x5555: raise ValueError('invalid signature')
        rows,stride,slots=fields[3],fields[4],fields[7]
        if not (rows and stride and slots): raise ValueError('zero geometry field')
        if not (rows <= MAX_ROWS and stride <= MAX_STRIDE and slots <= MAX_SLOTS):
            raise ValueError('geometry outside safe bounds')
        before=os.fstat(f.fileno())
        size=before.st_size
        limit = MAX_INPUT_BYTES if max_bytes is None else min(max_bytes, MAX_INPUT_BYTES)
        if size > limit: raise ValueError('input exceeds safe size limit')
        expected=HEADER+rows*slots*stride
        if size!=expected: raise ValueError(f'size mismatch: {size} != {expected}')
        digest=hashlib.sha256()
        f.seek(0)
        while block:=f.read(1024*1024): digest.update(block)
        after=os.fstat(f.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError('file changed during inspection')
    # These two address functions are permutations of the same payload.
    # Size and header alone cannot distinguish them.
    return {'source':str(path),'sha256':digest.hexdigest(),'size_bytes':size,
            'header_hex':h.hex(),'fields_u32_le':list(fields),
            'rows_candidate':rows,'stride_candidate':stride,'slots_candidate':slots,
            'expected_bytes':expected,'geometry_matches':True,
            'layout_candidates':{
              'row_major': 'offset=48+(row*slots+slot)*stride',
              'plane_major':'offset=48+(slot*rows+row)*stride'},
            'layout_discriminated':False,'channel_mapping':'unknown',
            'warning':'header and file length do not distinguish row-major from plane-major'}

def offsets(rows,slots,stride,row,slot):
    if not (0<=row<rows and 0<=slot<slots): raise IndexError('index outside raster')
    return (HEADER+(row*slots+slot)*stride, HEADER+(slot*rows+row)*stride)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('prt');p.add_argument('--output')
    a=p.parse_args(); result=json.dumps(inspect(a.prt),indent=2)
    if a.output: Path(a.output).write_text(result+'\n',encoding='utf-8')
    else: print(result)
