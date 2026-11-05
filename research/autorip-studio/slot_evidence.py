"""Read-only per-slot adjacency evidence for both candidate PRT layouts."""
from pathlib import Path
from layout_hypotheses import inspect, offsets


def compare_slots(path, *, pairs_per_slot=8, sample_bytes=256):
    if pairs_per_slot < 1 or sample_bytes < 1:
        raise ValueError('positive limits required')
    meta = inspect(path)
    rows, slots, stride = (meta[k] for k in ('rows_candidate','slots_candidate','stride_candidate'))
    if rows < 2:
        raise ValueError('at least two rows required')
    n = min(rows - 1, pairs_per_slot)
    row_ids = [(i * (rows - 1)) // n for i in range(n)]
    width = min(stride, sample_bytes)
    result = {}
    with Path(path).open('rb') as f:
        for layout in ('row_major','plane_major'):
            entries=[]
            for slot in range(slots):
                changed=equal=0
                for row in row_ids:
                    p=offsets(rows,slots,stride,row,slot)[0 if layout=='row_major' else 1]
                    q=offsets(rows,slots,stride,row+1,slot)[0 if layout=='row_major' else 1]
                    f.seek(p); a=f.read(width)
                    f.seek(q); b=f.read(width)
                    if len(a)!=width or len(b)!=width: raise ValueError('truncated sample')
                    diff=sum(x!=y for x,y in zip(a,b))
                    changed+=diff
                    equal+=(diff==0)
                entries.append({'slot_index':slot,'pairs':n,'compared_bytes':n*width,
                                'different_bytes':changed,'different_fraction':changed/(n*width),
                                'identical_pairs':equal})
            result[layout]=entries
    return {'source_sha256':meta['sha256'],'geometry':{'rows':rows,'slots':slots,'stride':stride},
            'sample_rows':row_ids,'bytes_per_pair':width,'hypotheses':result,
            'conclusion':'undetermined','channel_mapping':'unknown',
            'warning':'per-slot adjacency statistics are heuristic, not physical CMYKW identification'}
