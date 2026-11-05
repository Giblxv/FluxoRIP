"""Audit per-segment ternary bounds using derived aggregate evidence only.

Never reads PRT/ICC originals, emits no proprietary data, and never overwrites
an existing output. Segment boundaries are a hypothesis, not ink channels.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pairwise_bounds import equality_bounds
from safe_json_output import write_new_json

PAIRS = ('0_vs_50', '50_vs_100', '0_vs_100')
EXPECTED_HASHES = {
    'white_0': '75ef4acb3b7c2dbbce28dc112187ca19b250f2728842eae0c5c7c38b41d8d8ec',
    'white_50': '7f5d2036cf9a107a4600f21b3e54a9238850d73861c4de22d8871f3497d68773',
    'white_100': 'c143d3bac295c352ec63060ae20f0210c6dbf200e4f18fbee471e96d54c46136',
}


def audit(evidence: dict, *, require_known_hashes=True) -> dict:
    if evidence.get('schema') != 'autorip-candidate-plane-mask-periodicity-v1':
        raise ValueError('Unsupported evidence schema')
    hashes = evidence.get('source_sha256')
    if not isinstance(hashes, dict) or set(hashes) != set(EXPECTED_HASHES):
        raise ValueError('Source provenance missing')
    if require_known_hashes and hashes != EXPECTED_HASHES:
        raise ValueError('Unexpected PRT source hashes')
    geo = evidence['candidate_geometry']
    lines, stride, bands = (geo[k] for k in ('lines', 'stride', 'bands'))
    if any(type(x) is not int or x <= 0 for x in (lines, stride, bands)) or bands != 12:
        raise ValueError('Invalid candidate geometry')
    n = lines * stride
    if n > 8 * 1024**3:
        raise ValueError('Candidate segment too large')
    pair_results = evidence['pair_results']
    if set(pair_results) != set(PAIRS):
        raise ValueError('Unexpected pair names')
    for name in PAIRS:
        row = pair_results[name]
        counts = row['different_bytes_by_candidate_plane']
        if len(counts) != bands or any(type(x) is not int or not 0 <= x <= n for x in counts):
            raise ValueError('Invalid per-segment counts')
        if sum(counts) != row['total_different_bytes']:
            raise ValueError('Inconsistent aggregate totals')
    results = []
    for i in range(bands):
        ds = [pair_results[name]['different_bytes_by_candidate_plane'][i] for name in PAIRS]
        bounds = equality_bounds(n, *ds)
        results.append({'candidate_segment': i,
                        'pairwise_changed_bytes': dict(zip(PAIRS, ds)),
                        'all_distinct_min': bounds['all_distinct_min'],
                        'all_distinct_max': bounds['all_distinct_max'],
                        'parity': 'odd' if bounds['all_distinct_min'] % 2 else 'even'})
    global_bounds = equality_bounds(n * bands, *(pair_results[k]['total_different_bytes'] for k in PAIRS))
    minimum = sum(x['all_distinct_min'] for x in results)
    maximum = sum(x['all_distinct_max'] for x in results)
    if minimum < global_bounds['all_distinct_min'] or maximum > global_bounds['all_distinct_max']:
        raise AssertionError('Segment bounds violate global bounds')
    return {'schema': 'autorip-segment-ternary-bounds-audit-v1',
            'source_sha256': hashes, 'candidate_segment_bytes': n,
            'candidate_segment_count': bands, 'segments': results,
            'global_min_without_segment_counts': global_bounds['all_distinct_min'],
            'global_max_without_segment_counts': global_bounds['all_distinct_max'],
            'segment_informed_all_distinct_min': minimum,
            'segment_informed_all_distinct_max': maximum,
            'interpretation': 'At least this many original byte positions have three distinct values across 0/50/100 samples, if these derived counts are valid.',
            'limitations': ['No PRT/ICC read in this audit; source hashes are metadata from prior analysis, not freshly verified.',
                            'No channel, pixel, ink, Spot_1, CMYKW or 2-bit format inferred.',
                            'Segment boundaries are hypothetical; partition lower bound follows from supplied per-segment counts.']}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evidence', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    source = Path(args.evidence)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 2_000_000:
        raise ValueError('Evidence source must be a small regular non-symlink file')
    data = json.loads(source.read_text(encoding='utf-8'))
    write_new_json(args.output, audit(data))


if __name__ == '__main__':
    main()
