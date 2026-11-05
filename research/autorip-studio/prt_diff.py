"""Static read-only PRT diff; two layout hypotheses in one sequential payload pass."""
import argparse
import hashlib
import json
from pathlib import Path
from layout_hypotheses import inspect, HEADER


def compare(a, b, *, block_size=65536):
    if not isinstance(block_size, int) or not 1 <= block_size <= 8*1024*1024:
        raise ValueError('block_size outside 1..8388608')
    ma, mb = inspect(a), inspect(b)
    keys = ('rows_candidate', 'slots_candidate', 'stride_candidate')
    if any(ma[k] != mb[k] for k in keys):
        raise ValueError('incompatible geometries')
    rows, slots, stride = (ma[k] for k in keys)
    counters = {layout: [dict(slot_index=i, different_bytes=0,
                              compared_bytes=rows*stride, first_difference=None)
                         for i in range(slots)]
                for layout in ('row_major', 'plane_major')}
    hashes = [hashlib.sha256(), hashlib.sha256()]
    header_diffs = []
    with Path(a).open('rb') as fa, Path(b).open('rb') as fb:
        ha, hb = fa.read(HEADER), fb.read(HEADER)
        if len(ha) != HEADER or len(hb) != HEADER:
            raise ValueError('truncated header')
        hashes[0].update(ha); hashes[1].update(hb)
        header_diffs = [i for i, (x, y) in enumerate(zip(ha, hb)) if x != y]
        remaining = rows * slots * stride
        position = 0
        while remaining:
            n = min(remaining, block_size)
            aa, bb = fa.read(n), fb.read(n)
            if len(aa) != n or len(bb) != n:
                raise ValueError('truncated during comparison')
            hashes[0].update(aa); hashes[1].update(bb)
            cursor = 0
            while cursor < n:
                absolute_payload_offset = position + cursor
                cell, in_slot = divmod(absolute_payload_offset, stride)
                width = min(n-cursor, stride-in_slot)
                sa, sb = aa[cursor:cursor+width], bb[cursor:cursor+width]
                if sa != sb:
                    changed = [i for i, (x, y) in enumerate(zip(sa, sb)) if x != y]
                    row_major_slot = cell % slots
                    plane_major_slot = cell // rows
                    for layout, slot, row in (
                        ('row_major', row_major_slot, cell // slots),
                        ('plane_major', plane_major_slot, cell % rows),
                    ):
                        entry = counters[layout][slot]
                        entry['different_bytes'] += len(changed)
                        if entry['first_difference'] is None:
                            entry['first_difference'] = {
                                'row': row, 'byte_in_slot': in_slot + changed[0],
                                'absolute_offset': HEADER + absolute_payload_offset + changed[0]}
                cursor += width
            position += n
            remaining -= n
        if fa.read(1) or fb.read(1):
            raise ValueError('file grew during comparison')
    if hashes[0].hexdigest() != ma['sha256'] or hashes[1].hexdigest() != mb['sha256']:
        raise ValueError('file changed between inspection and comparison')
    for entries in counters.values():
        for entry in entries:
            entry['different_fraction'] = entry['different_bytes']/entry['compared_bytes']
    return {'a_sha256': ma['sha256'], 'b_sha256': mb['sha256'],
            'same_content': ma['sha256'] == mb['sha256'],
            'header_equal': not header_diffs,
            'header_changed_offsets': header_diffs,
            'geometry': {'rows': rows, 'slots': slots, 'stride': stride},
            'hypotheses': counters,
            'warning': 'slot indices are not proven ink channels; difference alone does not establish white ink coverage'}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('a'); p.add_argument('b')
    p.add_argument('--output'); p.add_argument('--block-size', type=int, default=65536)
    args = p.parse_args()
    obj = compare(args.a, args.b, block_size=args.block_size)
    data = json.dumps(obj, indent=2) + '\n'
    if args.output:
        Path(args.output).write_text(data, encoding='utf8')
    else:
        print(data)
