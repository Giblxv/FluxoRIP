# AutoRIP Studio — 2-bit symbol experiment (v0.70, 2026-11-04)

This research branch adds a read-only NumPy scanner and seven synthetic tests. The tested sources do **not** generate printable PRTs, interact with printer hardware, or execute proprietary software.

## Real evidence — three operator-labeled PRTs

Each PRT has 265,155,120 bytes, a candidate 0x5555 signature, and geometry 48 + 1456 × 12 × 15176. Labels white 0%, 50% and 100% were provided by the operator, not inferred from binary content. Whole-file SHA-256 was recalculated during sequential read:

- 0%: 75ef4acb3b7c2dbbce28dc112187ca19b250f2728842eae0c5c7c38b41d8d8ec
- 50%: 7f5d2036cf9a107a4600f21b3e54a9238850d73861c4de22d8871f3497d68773
- 100%: c143d3bac295c352ec63060ae20f0210c6dbf200e4f18fbee471e96d54c46136

At byte locations differing between 0% and 100%: 18,520,514 bytes and 74,003,852 changed 2-bit groups. Triad 0→1→3 occurs 61,669,540 times, and 0→3→3 occurs 12,332,286 times. No strictly descending changed 2-bit triads were found. Remaining patterns and per-lane counts are in the local derived report, which contains no original PRT bytes.

## Reproduction and limitations

Run synthetic tests: python -m unittest test_bitplane_probe -v (NumPy required). To analyze operator-provided files, use --white-0, --white-50, --white-100 and --output pointing to a separate result file.

The new 7 tests passed. In a clean combined work directory with v0.69 + previous forensic five tests, all 87 tests passed.

**Hypothesis, not fact:** groups of two bits may encode quantized levels; physical pixel layout, Spot_1 association, and white ink semantics have NOT been proven. Do not merge into production or upload proprietary PRT/ICC files.

Next steps: controlled isolation of individual Spot channels, known small artwork experiments, layout consistency tests, Windows 10/11 validation.
