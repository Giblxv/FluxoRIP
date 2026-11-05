"""Tighten ternary bounds using SHA-256 equality of pairwise difference masks.

Only consumes derived JSON evidence, never opens PRTs or ICCs. Equal digests
are treated as evidence of equal masks under the cryptographic collision
assumption, not as proof of a printer layout or physical channel.
"""
import argparse
import json
from pathlib import Path

from plane_bounds_audit import audit
from safe_json_output import write_new_json

PAIRS = ('0_vs_50', '50_vs_100', '0_vs_100')


def tighten(evidence):
    baseline = audit(evidence)
    rows = evidence['pair_results']
    n = baseline['candidate_segment_bytes']
    segments = []
    for i, prior in enumerate(baseline['segments']):
        digests = {p: rows[p]['difference_mask_sha256_by_candidate_plane'][i] for p in PAIRS}
        if any(not isinstance(v, str) or len(v) != 64 or
               any(c not in '0123456789abcdef' for c in v) for v in digests.values()):
            raise ValueError('Invalid SHA-256 digest')
        ds = {p: rows[p]['different_bytes_by_candidate_plane'][i] for p in PAIRS}
        if len(set(digests.values())) == 1:
            # Three equal pairwise difference masks => each changed position
            # has three different byte values.
            if len(set(ds.values())) != 1:
                raise ValueError('Equal masks have unequal counts')
            lo = hi = ds['0_vs_50']
            rule = 'all_three_masks_equal'
        elif digests['0_vs_50'] == digests['0_vs_100']:
            if ds['0_vs_50'] != ds['0_vs_100']:
                raise ValueError('Equal masks have unequal counts')
            lo = hi = ds['50_vs_100']
            rule = '0_vs_50_mask_equals_0_vs_100_mask'
        elif digests['0_vs_50'] == digests['50_vs_100']:
            if ds['0_vs_50'] != ds['50_vs_100']:
                raise ValueError('Equal masks have unequal counts')
            lo = hi = ds['0_vs_100']
            rule = '0_vs_50_mask_equals_50_vs_100_mask'
        elif digests['50_vs_100'] == digests['0_vs_100']:
            if ds['50_vs_100'] != ds['0_vs_100']:
                raise ValueError('Equal masks have unequal counts')
            lo = hi = ds['0_vs_50']
            rule = '50_vs_100_mask_equals_0_vs_100_mask'
        else:
            lo, hi = prior['all_distinct_min'], prior['all_distinct_max']
            rule = 'aggregate_counts_only'
        if not 0 <= lo <= hi <= n or lo < prior['all_distinct_min'] or hi > prior['all_distinct_max']:
            raise ValueError('Mask evidence contradicts pairwise counts')
        segments.append({'candidate_segment': i, 'all_distinct_min': lo,
                         'all_distinct_max': hi, 'inference': rule})
    return {'schema': 'autorip-mask-equality-ternary-bounds-v1',
            'source_sha256': baseline['source_sha256'],
            'candidate_segment_bytes': n, 'segments': segments,
            'all_distinct_min': sum(x['all_distinct_min'] for x in segments),
            'all_distinct_max': sum(x['all_distinct_max'] for x in segments),
            'limitations': ['Uses previously derived mask digests and counts, not freshly read PRTs.',
                            'SHA-256 digest equality is treated as mask equality under collision resistance.',
                            '12 contiguous candidate segments do not establish ink or channel layout.',
                            'No ICC or DeviceN/Spot_1 mapping is inferred.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = Path(args.evidence)
    if src.is_symlink() or not src.is_file() or src.stat().st_size > 2_000_000:
        raise ValueError('Evidence must be a small regular non-symlink file')
    result = tighten(json.loads(src.read_text(encoding='utf-8')))
    write_new_json(args.output, result)


if __name__ == '__main__':
    main()