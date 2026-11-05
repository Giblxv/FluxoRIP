# AutoRIP Studio — validation v0.82: modular holdout

Research-only; 2026-11-05. Branch `research/autorizado-autorip-studio`.

## Evidence and method

Three PRTs were fully rehashed against historical values from independent Library/Drive checks (v0.80/v0.81), then read only to calculate aggregate changed-byte counts. Every source is 265,155,120 bytes. The *candidate* period is 17,472 bytes (1,456 × 12) and the exploratory circular window is 1,456 bytes. The phase is selected using only the first payload half of operator-labelled 0%-vs-100% and subsequently held fixed for the second half and other comparisons.

| Comparison | Changed bytes train | Inside fixed window train | Changed bytes holdout | Inside fixed window holdout | Combined outside |
|---|---:|---:|---:|---:|---:|
| 0 vs 50 | 9,268,687 | 9,268,687 (100%) | 9,251,251 | 9,251,251 (100%) | 0 |
| 50 vs 100 | 9,266,413 | 9,266,125 (99.996892%) | 9,248,945 | 9,248,657 (99.996886%) | 576 |
| 0 vs 100 | 9,268,975 | 9,268,687 (99.996893%) | 9,251,539 | 9,251,251 (99.996887%) | 576 |

Training phase: 5,821; **four exactly tied best phases** in every comparison and half. Therefore the phase is *not uniquely identified*.

Training-only alternative candidate periods, with fixed window-to-period fraction 1/12 and reoptimized phase: 8,736 bytes → 50.10168%; 4,368 → 25.05084%; 2,184 → 12.52585%; 1,092 → 12.52564%. These are descriptive scores, not inferential probabilities or a proof of layout.

## Implementation

- `modular_holdout_audit.py`: read-only input descriptors, pinned operator-labelled SHA-256 baseline, independently recomputed digests, metadata checks, bounded chunks; only summary counts exported.
- `test_modular_holdout_audit.py`: 16 synthetic tests covering wraparound phase, holdout phase shift, shorter-period discrimination, varying read chunks, corruption, incorrect sizes/labels, symlinks/hardlinks, incorrect geometry, ambiguity and output privacy.
- GitHub Actions run [42081900085](https://github.com/Giblxv/FluxoRIP/actions/runs/42081900085): **52/52 on Windows and 52/52 on Ubuntu**, total 104 passing executions, zero skipped or failed.

## Limitations

The candidate period and window came from *earlier examination of these same PRTs*; splitting into halves is not independent replication. No 2-bit encoding, ink-channel mapping, spot semantics, ICC relationship, white dosage, printer compatibility, or generated PRT is claimed. Percentages 0/50/100 are operator-provided labels. FlexiPRINT is the RIP and PrintExp is the printer controller. No proprietary input bytes or ICC data were published; `main` was untouched.
