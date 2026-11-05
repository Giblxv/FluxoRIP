"""Read-only algebraic consistency checks for three bytewise difference counts.

No PRT parser, printer I/O, or proprietary sample required. These bounds cannot
identify white ink, Spot_1, channel order, bit depth, or actual PRT layout.
"""
from __future__ import annotations

import argparse
import json


def equality_bounds(n: int, d_0_50: int, d_50_100: int, d_0_100: int) -> dict:
    """Return feasible range for the count of all-distinct byte triples.

    Let x,y,z count the patterns 0=50!=100, 0=100!=50, 50=100!=0,
    and w count all-distinct triples. Every pairwise difference includes two
    of x/y/z plus w. Requiring x,y,z,w,all_equal >= 0 yields exact bounds.
    """
    vals = (n, d_0_50, d_50_100, d_0_100)
    if any(type(v) is not int for v in vals):
        raise TypeError('Counts must be integers, not booleans or floats')
    if n < 0 or any(d < 0 or d > n for d in vals[1:]):
        raise ValueError('Pairwise differences must lie between zero and n')
    ab, bc, ac = d_0_50, d_50_100, d_0_100
    s = ab + bc + ac
    lower = max(0, s - 2*n)
    upper = min(ab + ac - bc, ab + bc - ac, ac + bc - ab)
    if lower % 2 != s % 2:
        lower += 1
    if upper < lower:
        raise ValueError('No feasible equality partition for these pairwise counts')

    def partition(w):
        x = (ac + bc - ab - w)//2  # 0=50
        y = (ab + bc - ac - w)//2  # 0=100
        z = (ab + ac - bc - w)//2  # 50=100
        e = n - x - y - z - w
        assert min(x, y, z, e, w) >= 0
        return dict(all_equal=e, zero_equals_fifty=x,
                    zero_equals_hundred=y, fifty_equals_hundred=z,
                    all_distinct=w)

    return dict(schema='autorip-pairwise-equality-bounds-v1',
                bytes_per_sample=n,
                pairwise_differences=dict(zero_vs_fifty=ab,
                                          fifty_vs_hundred=bc,
                                          zero_vs_hundred=ac),
                all_distinct_min=lower, all_distinct_max=upper,
                all_distinct_step=2,
                example_partition_min=partition(lower),
                example_partition_max=partition(upper),
                caveat='Byte-level combinatorics only; no channel or 2-bit inference.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bytes-per-sample', type=int, required=True)
    ap.add_argument('--zero-vs-fifty', type=int, required=True)
    ap.add_argument('--fifty-vs-hundred', type=int, required=True)
    ap.add_argument('--zero-vs-hundred', type=int, required=True)
    a = ap.parse_args()
    print(json.dumps(equality_bounds(a.bytes_per_sample, a.zero_vs_fifty,
                                     a.fifty_vs_hundred, a.zero_vs_hundred), indent=2))


if __name__ == '__main__':
    main()
