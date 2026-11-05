"""Read-only deterministic layout evidence; no printer communication or ink inference."""
import argparse
import hashlib
import json
from pathlib import Path
from layout_hypotheses import inspect, offsets


def compare_layouts(path, *, max_pairs=240, sample_bytes=512):
    if max_pairs < 1 or sample_bytes < 1:
        raise ValueError('positive sampling limits required')
    meta = inspect(path)
    rows, slots, stride = (meta[k] for k in ('rows_candidate', 'slots_candidate', 'stride_candidate'))
    if rows < 2:
        raise ValueError('at least two rows required for adjacency comparison')
    width = min(stride, sample_bytes)
    total_pairs = (rows - 1) * slots
    count = min(max_pairs, total_pairs)
    # Stratified deterministic selection, spread over the complete logical raster.
    indices = [(i * total_pairs) // count for i in range(count)]
    metrics = {}
    with Path(path).open('rb') as f:
        for layout in ('row_major', 'plane_major'):
            changed = compared = equal_pairs = 0
            for idx in indices:
                row, slot = divmod(idx, slots)
                a, b = offsets(rows, slots, stride, row, slot)
                if layout == 'row_major':
                    oa, ob = a, offsets(rows, slots, stride, row+1, slot)[0]
                else:
                    oa, ob = b, offsets(rows, slots, stride, row+1, slot)[1]
                f.seek(oa); x = f.read(width)
                f.seek(ob); y = f.read(width)
                if len(x) != width or len(y) != width:
                    raise ValueError('unexpected truncation during sample')
                diff = sum(p != q for p, q in zip(x, y))
                changed += diff; compared += width
                equal_pairs += (diff == 0)
            metrics[layout] = {'pairs':count,'bytes_per_pair':width,
                               'compared_bytes':compared,'different_bytes':changed,
                               'different_fraction':changed/compared,
                               'identical_pairs':equal_pairs}
    return {'source_sha256':meta['sha256'], 'size_bytes':meta['size_bytes'],
            'geometry':{'rows':rows,'slots':slots,'stride':stride},
            'sampling':{'method':'stratified_deterministic','max_pairs':max_pairs,'sample_bytes':sample_bytes},
            'hypotheses':metrics,'conclusion':'undetermined',
            'caution':'adjacent-row similarity is heuristic; neither layout nor CMYKW mapping is proven'}

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('prt');p.add_argument('--output');p.add_argument('--max-pairs',type=int,default=240);p.add_argument('--sample-bytes',type=int,default=512)
    a=p.parse_args(); result=json.dumps(compare_layouts(a.prt,max_pairs=a.max_pairs,sample_bytes=a.sample_bytes),indent=2)
    if a.output: Path(a.output).write_text(result+'\n',encoding='utf-8')
    else: print(result)
