# AutoRIP Studio — Validation v0.80 (read-only)

Date: 2026-11-05. Branch: research/autorizado-autorip-studio.

## Source provenance

Three original PRT files were materialized as **temporary local copies from the user's ChatGPT Library**. Every file contained 265,155,120 bytes. Fresh SHA-256 reads using sha256sum, followed by the independent read-only Python verifier, matched previously archived reference digests.

| Operator label | Filename | SHA-256 |
|---|---|---|
| white_0 (0%) | TESTER1.PRT | 75ef4acb3b7c2dbbce28dc112187ca19b250f2728842eae0c5c7c38b41d8d8ec |
| white_50 (50%) | TESTER1_1.PRT | 7f5d2036cf9a107a4600f21b3e54a9238850d73861c4de22d8871f3497d68773 |
| white_100 (100%) | TESTER1_0.PRT | c143d3bac295c352ec63060ae20f0210c6dbf200e4f18fbee471e96d54c46136 |

Percentages are operator-supplied labels and not measured ink settings. The current **Google Drive copies were checked for size only**, not rehashed. Historical reference values are from previous analyses of this sample set, not a vendor attestation.

## Verified full re-analysis

The research analyzer read all three Library copies in full. Its calculated source digests matched the trusted local verification manifest.

- all_equal: 246,634,558
- zero_equals_fifty: 576
- zero_equals_hundred: 0
- fifty_equals_hundred: 5,156
- all_distinct: 18,514,782
- changed 0 vs 50: 18,519,938 bytes
- changed 50 vs 100: 18,515,358 bytes
- changed 0 vs 100: 18,520,514 bytes

Candidate geometry: header 48 bytes, 1,456 lines, stride 15,176 bytes, and 12 candidate regions. These do **not** establish channels, Spot_1, two-bit encoding, ICC mapping or physical ink behavior.

## Regressions

- Local consolidated archived modules: 49/49 synthetic tests passed, including nine new tests. This local suite is not identical to the current CI suite.
- GitHub Actions [run 42072224088](https://github.com/Giblxv/FluxoRIP/actions/runs/42072224088): **31/31 synthetic tests passed** on commit 00a3b45479728e01ec0eea81e5851b5207b68c8b.
- Added verify_sample_hashes.py and test_verify_sample_hashes.py; updated CI workflow.
- No proprietary PRT/ICC bytes or printer commands were committed.

## Remaining validation

Rehash current Google Drive copies; extend source replacement/race tests; investigate byte-layout semantics without asserting compatibility with Hoson/PrintExp or generating printer-ready output.
