"""Read-only equality-pattern analysis for three operator-labelled PRT samples.

Classifies each byte position without assuming channels, bit-depth, or ink meaning.
Output is only aggregate counts and hashes. Does not create printer-ready files.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import stat
import struct
import numpy as np

from safe_json_output import write_new_json

HEADER = 48
BANDS = 12
LABELS = ('white_0', 'white_50', 'white_100')
CLASSES = ('all_equal', 'zero_equals_fifty', 'zero_equals_hundred',
           'fifty_equals_hundred', 'all_distinct')


def analyze(paths, *, chunk_bytes=1024 * 1024):
    if set(paths) != set(LABELS):
        raise ValueError('Exactly three operator-labelled inputs required')
    if not 1 <= chunk_bytes <= 8 * 1024 * 1024:
        raise ValueError('chunk_bytes out of bounds')
    files = []
    stats = []
    heads = []
    for label in LABELS:
        source = Path(paths[label])
        if source.is_symlink():
            raise ValueError('Source symlinks rejected')
        source = source.resolve(strict=True)
        st = source.stat()
        if not stat.S_ISREG(st.st_mode) or not HEADER <= st.st_size <= 8 * 1024**3:
            raise ValueError('Invalid source size or type')
        with source.open('rb') as fd:
            head = fd.read(HEADER)
        if len(head) != HEADER or struct.unpack_from('<H', head)[0] != 0x5555:
            raise ValueError('Candidate signature missing')
        files.append(source)
        stats.append((st.st_size, st.st_mtime_ns, st.st_ino, st.st_dev))
        heads.append(head)
    if len(set(files)) != 3 or len(set((s[2], s[3]) for s in stats)) != 3:
        raise ValueError('Distinct source inodes required')
    if len(set(heads)) != 1 or len(set(s[0] for s in stats)) != 1:
        raise ValueError('Incompatible source headers or sizes')
    lines, stride, bands = (struct.unpack_from('<I', heads[0], k)[0] for k in (12, 16, 28))
    if not (1 <= lines <= 10_000_000 and 1 <= stride <= 1_000_000 and bands == BANDS):
        raise ValueError('Invalid candidate geometry')
    plane_length = lines * stride
    if HEADER + bands * plane_length != stats[0][0]:
        raise ValueError('Candidate geometry inconsistent with file size')
    hashes = [sha256() for _ in LABELS]
    by_plane = []
    streams = [p.open('rb') for p in files]
    try:
        for stream, head, digest in zip(streams, heads, hashes):
            actual = stream.read(HEADER)
            if actual != head:
                raise ValueError('Source header changed')
            digest.update(actual)
        for plane in range(bands):
            counts = np.zeros(len(CLASSES), dtype=np.int64)
            remaining = plane_length
            while remaining:
                size = min(chunk_bytes, remaining)
                chunks = [s.read(size) for s in streams]
                if any(len(c) != size for c in chunks):
                    raise ValueError('Source truncated')
                for h, c in zip(hashes, chunks):
                    h.update(c)
                a, b, c = (np.frombuffer(x, dtype=np.uint8) for x in chunks)
                ab, ac, bc = a == b, a == c, b == c
                # Mutually exclusive partition: 5 possible equality patterns.
                increments = (
                    np.count_nonzero(ab & ac),
                    np.count_nonzero(ab & ~ac),
                    np.count_nonzero(ac & ~ab),
                    np.count_nonzero(bc & ~ab),
                    np.count_nonzero(~ab & ~ac & ~bc),
                )
                counts += np.array(increments, dtype=np.int64)
                remaining -= size
            if int(counts.sum()) != plane_length:
                raise AssertionError('Equality partition is not exhaustive')
            by_plane.append(dict(zip(CLASSES, map(int, counts))))
        if any(s.read(1) for s in streams):
            raise ValueError('Source grew during scan')
    finally:
        for stream in streams:
            stream.close()
    for p, before in zip(files, stats):
        after = p.stat()
        if (after.st_size, after.st_mtime_ns, after.st_ino, after.st_dev) != before:
            raise ValueError('Source metadata changed during scan')
    totals = {key: sum(row[key] for row in by_plane) for key in CLASSES}
    # Every byte belongs to exactly one class; pairwise counts follow algebraically.
    derived = {
        '0_vs_50': totals['zero_equals_hundred'] + totals['fifty_equals_hundred'] + totals['all_distinct'],
        '50_vs_100': totals['zero_equals_fifty'] + totals['zero_equals_hundred'] + totals['all_distinct'],
        '0_vs_100': totals['zero_equals_fifty'] + totals['fifty_equals_hundred'] + totals['all_distinct'],
    }
    return {
        'schema': 'autorip-ternary-byte-equality-v1',
        'operator_labels': list(LABELS),
        'source_sha256': dict(zip(LABELS, [h.hexdigest() for h in hashes])),
        'candidate_geometry': {'header_bytes': HEADER, 'lines': lines, 'stride': stride, 'bands': bands},
        'counts_by_candidate_plane': by_plane,
        'totals': totals,
        'derived_pairwise_changed_byte_counts': derived,
        'interpretation': 'Five mutually exclusive equality patterns at each byte offset, not pixel or ink identities.',
        'limitations': ['Candidate contiguous 12-plane layout is unproven.',
                        '0/50/100 labels are operator-supplied, not measured ink output.',
                        'No 2-bit encoding, Spot_1, CMYKW or ICC mapping is inferred.',
                        'Stat checks and SHA-256 are not an atomic snapshot.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for label in LABELS:
        parser.add_argument('--' + label.replace('_', '-'), required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    paths = {label: getattr(args, label) for label in LABELS}
    output = Path(args.output)
    if output.resolve() in {Path(p).resolve() for p in paths.values()}:
        raise ValueError('Output cannot be a source')
    result = analyze(paths)
    write_new_json(output, result)
    print('Wrote aggregate evidence to', output)


if __name__ == '__main__':
    main()