"""Experimental read-only 2-bit symbol transition analysis of a labeled PRT triplet.

The 0/50/100 labels describe the operator's settings, not inferred raster values.
Symbol lanes (low-to-high inside each byte) are hypotheses, not decoded pixels.
Does NOT generate PRTs, execute FlexiPRINT, or control hardware.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct
import numpy as np

HEADER = 48
MAX_BYTES = 8 * 1024**3
EXPECTED_BANDS = 12
NAMES = ('white_0', 'white_50', 'white_100')


def _metadata(path):
    p = Path(path).resolve(strict=True)
    if not p.is_file():
        raise ValueError('Not a regular file')
    s = p.stat()
    if s.st_size < HEADER or s.st_size > MAX_BYTES:
        raise ValueError('PRT size exceeds safety bounds')
    with p.open('rb') as f:
        header = f.read(HEADER)
    if len(header) != HEADER or struct.unpack_from('<H', header, 0)[0] != 0x5555:
        raise ValueError('Missing candidate PRT signature')
    lines, stride, bands = [struct.unpack_from('<I', header, i)[0]
                           for i in (12, 16, 28)]
    if not (0 < lines <= 10_000_000 and 0 < stride <= 1_000_000
            and bands == EXPECTED_BANDS):
        raise ValueError('Invalid candidate PRT geometry fields')
    if HEADER + lines * stride * bands != s.st_size:
        raise ValueError('Candidate PRT geometry does not match file size')
    return p, s, header, (lines, stride, bands)


def analyze_symbol_transitions(paths, *, chunk_bytes=1024 * 1024):
    """Hash and inspect originals in one pass, without storing original payloads.

    Analysis is restricted to byte positions that change between 0 and 100.
    This intentionally excludes identical positions from symbol histograms and
    cannot be interpreted as an estimate of the frequency of ink colors.
    """
    if set(paths) != set(NAMES):
        raise ValueError('Exactly white_0, white_50 and white_100 are required')
    if not (1 <= chunk_bytes <= 16 * 1024 * 1024):
        raise ValueError('Chunk size outside safe bounds')
    metadata = [_metadata(paths[name]) for name in NAMES]
    p, stats, heads, geom = zip(*metadata)
    if len(set(p)) != 3:
        raise ValueError('Distinct source paths required')
    if len(set(geom)) != 1:
        raise ValueError('All files must share candidate geometry')
    hashes = [sha256() for _ in NAMES]
    hist = np.zeros((4, 64), dtype=np.int64)
    changed_bytes = 0
    all_bytes_ascending = 0
    changed_symbols = 0
    ascending_changed_symbols = 0
    descending_changed_symbols = 0
    total_payload = geom[0][0] * geom[0][1] * geom[0][2]
    source_stats = [(s.st_size, s.st_mtime_ns, s.st_ino) for s in stats]
    streams = [x.open('rb') for x in p]
    try:
        first = [f.read(HEADER) for f in streams]
        if any(h != h_original for h, h_original in zip(first, heads)):
            raise ValueError('PRT header changed before reading')
        for digest, header in zip(hashes, first):
            digest.update(header)
        left = total_payload
        while left:
            n = min(left, chunk_bytes)
            buffers = [f.read(n) for f in streams]
            if any(len(b) != n for b in buffers):
                raise ValueError('Truncated PRT during analysis')
            for h, raw in zip(hashes, buffers):
                h.update(raw)
            a, b, c = (np.frombuffer(z, dtype=np.uint8) for z in buffers)
            mask = a != c
            count = int(np.count_nonzero(mask))
            changed_bytes += count
            if count:
                x, y, z = a[mask], b[mask], c[mask]
                all_bytes_ascending += int(np.count_nonzero((x < y) & (y < z)))
                for lane in range(4):
                    shift = 2 * lane
                    s0, s50, s100 = ((v >> shift) & 3 for v in (x, y, z))
                    codes = (s0.astype(np.uint8)
                             | (s50.astype(np.uint8) << 2)
                             | (s100.astype(np.uint8) << 4))
                    hist[lane] += np.bincount(codes, minlength=64).astype(np.int64)
                    neq = s0 != s100
                    changed_symbols += int(np.count_nonzero(neq))
                    ascending_changed_symbols += int(np.count_nonzero(neq & (s0 < s50) & (s50 < s100)))
                    descending_changed_symbols += int(np.count_nonzero(neq & (s0 > s50) & (s50 > s100)))
            left -= n
        if any(f.read(1) for f in streams):
            raise ValueError('PRT grew during reading')
    finally:
        for f in streams:
            f.close()
    for pp, orig in zip(p, source_stats):
        now = pp.stat()
        if (now.st_size, now.st_mtime_ns, now.st_ino) != orig:
            raise ValueError('Input changed during analysis')
    patterns = []
    for code in range(64):
        total = int(hist[:, code].sum())
        if total:
            patterns.append({'symbols_0_50_100': [code & 3, (code >> 2) & 3, (code >> 4) & 3],
                             'count': total,
                             'per_lane_low_to_high': hist[:, code].tolist()})
    patterns.sort(key=lambda x: (-x['count'], x['symbols_0_50_100']))
    if int(hist.sum()) != 4 * changed_bytes:
        raise ValueError('Internal histogram integrity error')
    return {
        'scope': 'only byte positions differing between 0% and 100% samples',
        'input_sha256': dict(zip(NAMES, [h.hexdigest() for h in hashes])),
        'input_bytes': int(HEADER + total_payload),
        'geometry_hypothesis': {'header_bytes': HEADER, 'lines': geom[0][0],
                                'stride': geom[0][1], 'bands': geom[0][2]},
        'changed_bytes_0_vs_100': changed_bytes,
        'strictly_ascending_full_byte_triplets_among_changed_bytes': all_bytes_ascending,
        'changed_2bit_symbols_0_vs_100': changed_symbols,
        'strict_ascending_changed_2bit_symbols': ascending_changed_symbols,
        'strict_descending_changed_2bit_symbols': descending_changed_symbols,
        'most_common_symbol_patterns': patterns[:25],
        'full_histogram_4_lanes_64_codes': hist.tolist(),
        'limitations': [
            'Two-bit groups are a candidate coding interpretation, not decoded pixels.',
            'The nominal 50% setting need not linearly interpolate every 2-bit symbol.',
            'No physical channel/Spot mapping follows from 2-bit symbol transitions.',
            'Changed-byte filtering excludes fixed positions from histogram counts.',
            'Input integrity is checked via SHA-256 and stat before/after, not a locked filesystem snapshot.'
        ]
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in NAMES:
        ap.add_argument('--' + name.replace('_', '-'), required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    files = {name: getattr(args, name) for name in NAMES}
    output = Path(args.output).resolve()
    if output in {Path(x).resolve() for x in files.values()}:
        raise ValueError('Output cannot overwrite input')
    report = analyze_symbol_transitions(files)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"changed bytes={report['changed_bytes_0_vs_100']}, changed 2bit symbols={report['changed_2bit_symbols_0_vs_100']}")
    print(f'Saved {output}')


if __name__ == '__main__':
    main()
