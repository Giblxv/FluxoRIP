"""Fingerprint candidate-plane change masks for a 0/50/100 PRT triplet.

Read-only forensic tool. The 12 planes and 2-bit behavior are HYPOTHESES,
not proven ink channels, printheads, nozzle passes or decoded pixels.
No printer/driver calls or proprietary executable code.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import stat as statlib
import struct

import numpy as np
from safe_json_output import write_new_json

HEADER_BYTES = 48
MAX_FILE_BYTES = 8 * 1024**3
MAX_STRIDE = 1_000_000
MAX_LINES = 10_000_000
BANDS = 12
KEYS = ('white_0', 'white_50', 'white_100')
PAIRS = ('0_vs_50', '50_vs_100', '0_vs_100')


def _source(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Symlink sources are not accepted')
    path = path.resolve(strict=True)
    before = path.stat()
    if not statlib.S_ISREG(before.st_mode):
        raise ValueError('Expected a regular source file')
    if not HEADER_BYTES <= before.st_size <= MAX_FILE_BYTES:
        raise ValueError('Source file size outside safe bounds')
    with path.open('rb') as fd:
        head = fd.read(HEADER_BYTES)
    if len(head) != HEADER_BYTES or struct.unpack_from('<H', head)[0] != 0x5555:
        raise ValueError('Candidate PRT 0x5555 signature missing')
    lines, stride, bands = (struct.unpack_from('<I', head, i)[0] for i in (12, 16, 28))
    if not (0 < lines <= MAX_LINES and 0 < stride <= MAX_STRIDE and bands == BANDS):
        raise ValueError('Invalid candidate geometry; twelve bands required')
    if HEADER_BYTES + lines * stride * bands != before.st_size:
        raise ValueError('Candidate geometry is inconsistent with file length')
    return path, before, head, (lines, stride, bands)


def _groups_by_fingerprint(fps):
    seen = {}
    for i, digest in enumerate(fps):
        seen.setdefault(digest, []).append(i)
    return sorted((g for g in seen.values() if len(g) > 1), key=lambda x: x[0])


def inspect_periodicity(paths, *, chunk_bytes=2 * 1024 * 1024):
    """SHA-256 of a 0/1 byte mask per candidate plane, for every pair.

    Original file contents are never copied to the output and are never opened
    for writing. Arrays are bounded by chunk_bytes. SHA-256 verifies the entire
    input once per execution; stat comparison detects observed mutations.
    """
    if set(paths) != set(KEYS):
        raise ValueError('Require labeled white_0, white_50 and white_100 files')
    if not 1 <= chunk_bytes <= 8 * 1024 * 1024:
        raise ValueError('chunk_bytes outside bounded range')
    sources = [_source(paths[k]) for k in KEYS]
    filenames, metadata, headers, geometries = zip(*sources)
    if len(set(filenames)) != 3:
        raise ValueError('Three different file paths are required')
    if len(set(geometries)) != 1 or len(set(headers)) != 1:
        raise ValueError('Incompatible candidate geometry or distinct PRT headers')
    lines, stride, bands = geometries[0]
    plane_length = lines * stride
    checks = [(s.st_size, s.st_mtime_ns, s.st_ino) for s in metadata]
    source_digests = [sha256() for _ in KEYS]
    mask_hashes = {key: [] for key in PAIRS}
    changed_byte_counts = {key: [] for key in PAIRS}
    streams = [p.open('rb') for p in filenames]
    try:
        for expected, fd, digest in zip(headers, streams, source_digests):
            observed = fd.read(HEADER_BYTES)
            if observed != expected:
                raise ValueError('PRT header changed before scanning')
            digest.update(observed)
        for _plane in range(bands):
            plane_hashes = {pair: sha256() for pair in PAIRS}
            counts = {pair: 0 for pair in PAIRS}
            left = plane_length
            while left:
                n = min(chunk_bytes, left)
                blocks = [fd.read(n) for fd in streams]
                if any(len(block) != n for block in blocks):
                    raise ValueError('PRT truncated during inspection')
                for digest, block in zip(source_digests, blocks):
                    digest.update(block)
                a, b, c = (np.frombuffer(block, dtype=np.uint8) for block in blocks)
                masks = (a != b, b != c, a != c)
                for pair, mask in zip(PAIRS, masks):
                    plane_hashes[pair].update(mask.tobytes())
                    counts[pair] += int(np.count_nonzero(mask))
                left -= n
            for pair in PAIRS:
                mask_hashes[pair].append(plane_hashes[pair].hexdigest())
                changed_byte_counts[pair].append(counts[pair])
        if any(fd.read(1) for fd in streams):
            raise ValueError('Source grew during inspection')
    finally:
        for fd in streams:
            fd.close()
    for path, original in zip(filenames, checks):
        current = path.stat()
        if (current.st_size, current.st_mtime_ns, current.st_ino) != original:
            raise ValueError('Source metadata changed during inspection')

    # Report exact SHA-256 mask coincidences, not inferred channel identities.
    detail = {}
    for pair in PAIRS:
        fingerprints = mask_hashes[pair]
        detail[pair] = {
            'different_bytes_by_candidate_plane': changed_byte_counts[pair],
            'total_different_bytes': sum(changed_byte_counts[pair]),
            'difference_mask_sha256_by_candidate_plane': fingerprints,
            'equal_mask_groups': _groups_by_fingerprint(fingerprints),
            'interior_planes_1_to_10_repeat_with_period_3': all(
                fingerprints[i] == fingerprints[i + 3] for i in range(1, 8)
            ),
        }
    return {
        'schema': 'autorip-candidate-plane-mask-periodicity-v1',
        'candidate_geometry': {'header_bytes': HEADER_BYTES, 'lines': lines,
                               'stride': stride, 'bands': bands},
        'source_sha256': dict(zip(KEYS, (h.hexdigest() for h in source_digests))),
        'mask_interpretation': 'one byte per original byte: 0=unchanged, 1=changed',
        'candidate_layout': 'plane_major (hypothetical contiguous plane blocks)',
        'pair_results': detail,
        'caveats': [
            'A matching difference mask only means the changed positions coincide.',
            'Plane boundaries, inks, Spot channels and per-pixel encoding remain unproven.',
            'Source labels were supplied by the operator.',
            'Stat checks and SHA-256 are not an atomic locked snapshot.',
            'No source files are written and no printer commands are issued.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for label in KEYS:
        parser.add_argument('--' + label.replace('_', '-'), required=True)
    parser.add_argument('--output', required=True, help='JSON destination, never a source path')
    options = parser.parse_args()
    source_paths = {label: getattr(options, label) for label in KEYS}
    output = Path(options.output).resolve()
    if output in {Path(path).resolve() for path in source_paths.values()}:
        raise ValueError('Output cannot be an original source')
    evidence = inspect_periodicity(source_paths)
    write_new_json(output, evidence)
    print('Derived evidence written to', output)


if __name__ == '__main__':
    main()
