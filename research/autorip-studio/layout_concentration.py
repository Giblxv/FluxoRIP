"""Read-only candidate-layout concentration probe for operator-labeled PRT triplets.

This diagnoses whether the changed bytes concentrate in logical slots under three
hypothetical layouts. No channel, ink color, pixel format or printer output is inferred.
The input files are opened only in binary-read mode. Third-party binaries are not run.
"""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import argparse
import json
import struct
import numpy as np

HEADER_BYTES = 48
MAX_BYTES = 8 * 1024**3
EXPECTED_BANDS = 12
NAMES = ('white_0', 'white_50', 'white_100')


def _metadata(path):
    p = Path(path).resolve(strict=True)
    if not p.is_file():
        raise ValueError('Input must be a regular file')
    stat = p.stat()
    if not HEADER_BYTES <= stat.st_size <= MAX_BYTES:
        raise ValueError('Input size outside limits')
    with p.open('rb') as f:
        h = f.read(HEADER_BYTES)
    if len(h) != HEADER_BYTES or struct.unpack_from('<H', h)[0] != 0x5555:
        raise ValueError('Candidate PRT signature absent')
    lines, stride, bands = (struct.unpack_from('<I', h, k)[0] for k in (12, 16, 28))
    if not (1 <= lines <= 10_000_000 and 1 <= stride <= 1_000_000 and bands == EXPECTED_BANDS):
        raise ValueError('Candidate PRT geometry invalid or not 12-band')
    if HEADER_BYTES + lines * stride * bands != stat.st_size:
        raise ValueError('Candidate geometry is inconsistent with file length')
    return p, stat, h, (lines, stride, bands)


def _summary(counts):
    counts = [int(n) for n in counts]
    total = sum(counts)
    return {
        'count_by_candidate_band': counts,
        'total': total,
        'maximum_band_share': max(counts, default=0) / total if total else 0.0,
        'min_to_max_ratio': min(counts) / max(counts) if max(counts, default=0) else None,
    }


def analyze_concentration(paths, *, chunk_bytes=4 * 1024 * 1024):
    if set(paths) != set(NAMES):
        raise ValueError('All three explicitly labeled input paths are required')
    if not 1 <= chunk_bytes <= 16 * 1024 * 1024:
        raise ValueError('Chunk size outside bounded range')
    items = [_metadata(paths[n]) for n in NAMES]
    ps, stats, headers, geoms = zip(*items)
    if len(set(ps)) != 3:
        raise ValueError('Three distinct source paths required')
    if len(set(geoms)) != 1:
        raise ValueError('Incompatible candidate geometries')
    if len(set(headers)) != 1:
        raise ValueError('Headers are not identical; experiment not comparable')
    lines, stride, bands = geoms[0]
    orig_stats = [(s.st_size, s.st_mtime_ns, s.st_ino) for s in stats]
    counts = {name: np.zeros(bands, dtype=np.int64)
              for name in ('row_major', 'plane_major', 'byte_interleaved')}
    pairs = ('0_vs_50', '50_vs_100', '0_vs_100')
    differences = {k: {name: np.zeros(bands, dtype=np.int64) for name in counts} for k in pairs}
    digests = [sha256() for _ in ps]
    streams = [p.open('rb') for p in ps]
    try:
        for i, stream in enumerate(streams):
            header = stream.read(HEADER_BYTES)
            if header != headers[i]:
                raise ValueError('Input changed before payload read')
            digests[i].update(header)
        for offset in range(0, lines * stride * bands, chunk_bytes):
            size = min(chunk_bytes, lines * stride * bands - offset)
            buf = [s.read(size) for s in streams]
            if any(len(b) != size for b in buf):
                raise ValueError('Input truncated during scan')
            for dig, b in zip(digests, buf):
                dig.update(b)
            a, b, c = (np.frombuffer(raw, dtype=np.uint8) for raw in buf)
            masks = dict(zip(pairs, (a != b, b != c, a != c)))
            for pair, mask in masks.items():
                ix = np.flatnonzero(mask).astype(np.int64)
                if not ix.size:
                    continue
                byte_positions = ix + offset
                cell = byte_positions // stride
                indices = {
                    'row_major': cell % bands,
                    'plane_major': cell // lines,
                    'byte_interleaved': byte_positions % bands,
                }
                for name, slot in indices.items():
                    differences[pair][name] += np.bincount(slot, minlength=bands).astype(np.int64)
        if any(stream.read(1) for stream in streams):
            raise ValueError('Input grew during scan')
    finally:
        for stream in streams:
            stream.close()
    for p, orig in zip(ps, orig_stats):
        stat = p.stat()
        if (stat.st_size, stat.st_mtime_ns, stat.st_ino) != orig:
            raise ValueError('Input metadata changed during scan')
    results = {pair: {name: _summary(diff[name]) for name in counts}
               for pair, diff in differences.items()}
    for pair in pairs:
        totals = {details['total'] for details in results[pair].values()}
        if len(totals) != 1:
            raise ValueError('Candidate layout count integrity check failed')
    return {
        'schema': 'autorip-layout-concentration-v1',
        'labels_are_operator_supplied': True,
        'geometry_hypothesis': {'header_bytes': HEADER_BYTES, 'lines': lines,
                                'stride': stride, 'bands': bands},
        'source_sha256': dict(zip(NAMES, (dig.hexdigest() for dig in digests))),
        'candidate_layout_counts': results,
        'limitations': [
            'No candidate layout is proven by distribution of changed bytes alone.',
            'The byte-interleaved hypothesis assumes a fixed 12-byte modular phase; actual order may differ.',
            'No Spot/white physical channel mapping is inferred.',
            'Input snapshots are not locked; SHA and stat detect only the observed version.',
            'The tool never writes to its source files.',
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in NAMES:
        ap.add_argument('--' + name.replace('_', '-'), required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    inputs = {k: getattr(args, k) for k in NAMES}
    output = Path(args.output).resolve()
    if output in {Path(x).resolve() for x in inputs.values()}:
        raise ValueError('Output must not overwrite an input')
    result = analyze_concentration(inputs)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('Scanned', result['geometry_hypothesis'], 'with source hashes:', result['source_sha256'])


if __name__ == '__main__':
    main()
