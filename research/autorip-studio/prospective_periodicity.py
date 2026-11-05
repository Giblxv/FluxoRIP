"""Prospective, *locked-parameter* replication of the v0.82 PRT mask hypothesis.

For NEW independent artwork only. Read-only, aggregate-only; never exports
source PRT bytes or emits a printer-ready file. No inference about channels,
2-bit pixels, ICC, white-ink dosage or Hoson compatibility is justified.

This experiment deliberately does NOT refit its 17472-byte candidate period,
1456-byte candidate window or 5821-byte candidate phase on new observations.
That phase was one of multiple equally-good positions in the historical set.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import stat
import struct

import numpy as np

from controlled_capture import ARTWORKS, load_plan, verify_capture_set
from safe_json_output import write_new_json

PERIOD = 17_472
WINDOW = 1_456
PHASE = 5_821
HEADER = 48
LEVEL_KEYS = (("white_0", 1), ("white_50", 1),
              ("white_100", 1), ("white_50", 2))
PAIRS = (
    ("0_vs_50", 0, 1),
    ("50_vs_100", 1, 2),
    ("0_vs_100", 0, 2),
    ("50_reexport", 1, 3),
)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _fixed_window_counts(block_a: bytes, block_b: bytes, offset: int):
    """Count byte differences inside and outside a *fixed*, preregistered window."""
    left = np.frombuffer(block_a, dtype=np.uint8)
    right = np.frombuffer(block_b, dtype=np.uint8)
    changed_positions = np.flatnonzero(left != right)
    if not changed_positions.size:
        return 0, 0
    phases = (changed_positions.astype(np.int64) + offset - PHASE) % PERIOD
    return int(changed_positions.size), int(np.count_nonzero(phases < WINDOW))


def _scan_artwork(records, base, *, chunk_bytes):
    """Rehash while comparing all 4 independently captured sources."""
    paths = [base / record["filename"] for record in records]
    pre = [p.lstat() for p in paths]
    if any(not stat.S_ISREG(s.st_mode) for s in pre):
        raise ValueError("Source is not a regular file")
    if len({(s.st_dev, s.st_ino) for s in pre}) != len(pre):
        raise ValueError("Source hardlink aliases rejected")
    with ExitStack() as stack:
        streams = []
        for path, info in zip(paths, pre):
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(path, flags)
            try:
                stream = os.fdopen(fd, "rb")
            except BaseException:
                os.close(fd)
                raise
            stack.enter_context(stream)
            if _identity(os.fstat(stream.fileno())) != _identity(info):
                raise ValueError("Source changed while opening")
            streams.append(stream)

        headers = [f.read(HEADER) for f in streams]
        result = {"candidate_period_bytes": PERIOD,
                  "candidate_window_bytes": WINDOW,
                  "locked_phase_bytes": PHASE}
        size = pre[0].st_size
        if len(set(headers)) != 1 or len(headers[0]) != HEADER:
            result.update(status="not_evaluable", reason="headers_not_identical")
            return result
        signature = struct.unpack_from("<H", headers[0], 0)[0]
        lines = struct.unpack_from("<I", headers[0], 12)[0]
        stride = struct.unpack_from("<I", headers[0], 16)[0]
        bands = struct.unpack_from("<I", headers[0], 28)[0]
        result["candidate_geometry"] = {"lines": lines, "stride": stride, "bands": bands}
        if (signature != 0x5555 or lines != WINDOW or bands != 12 or
                stride < 1 or HEADER + PERIOD * stride != size or
                any(s.st_size != size for s in pre)):
            result.update(status="not_evaluable", reason="does_not_match_locked_candidate_geometry")
            return result

        digests = [hashlib.sha256(h) for h in headers]
        totals = {name: [0, 0] for name, _, _ in PAIRS}
        for start in range(0, PERIOD * stride, chunk_bytes):
            count = min(chunk_bytes, PERIOD * stride - start)
            blocks = [stream.read(count) for stream in streams]
            if any(len(block) != count for block in blocks):
                raise ValueError("Source shortened during scan")
            for digest, block in zip(digests, blocks):
                digest.update(block)
            for name, i, j in PAIRS:
                changed, inside = _fixed_window_counts(blocks[i], blocks[j], start)
                totals[name][0] += changed
                totals[name][1] += inside
        if any(stream.read(1) for stream in streams):
            raise ValueError("Source grew while scanning")
        for path, info, stream, digest, record in zip(paths, pre, streams, digests, records):
            if (_identity(os.fstat(stream.fileno())) != _identity(info) or
                    not stat.S_ISREG(path.lstat().st_mode) or
                    _identity(path.lstat()) != _identity(info)):
                raise ValueError("Source changed during scan")
            if digest.hexdigest() != record["sha256"]:
                raise ValueError("SHA-256 mismatch after comparative scan")

    comparisons = {}
    for name, values in totals.items():
        changed, inside = values
        comparisons[name] = {
            "changed_bytes": changed,
            "inside_locked_window": inside,
            "outside_locked_window": changed - inside,
            "locked_window_share": inside / changed if changed else None,
        }
    reexport_changes = comparisons["50_reexport"]["changed_bytes"]
    level_counts = {pair: comparisons[pair]["changed_bytes"]
                    for pair in ("0_vs_50", "50_vs_100", "0_vs_100")}
    if reexport_changes:
        status = "repeatability_confounded"
    elif all(value == 0 for value in level_counts.values()):
        status = "no_level_difference_observed"
    elif level_counts["0_vs_100"] == 0:
        # Equal endpoints do not imply an unchanged intermediate (50%) export.
        status = "endpoints_equal_intermediate_differs"
    else:
        status = "descriptive_only_no_ink_inference"
    result.update(status=status, comparisons=comparisons,
                  white_50_reexport_byte_identical=(reexport_changes == 0))
    return result


def analyze(plan, directory, *, chunk_bytes=1024 * 1024):
    """No optional period/phase fitting, no data-driven candidate changes."""
    if type(chunk_bytes) is not int or not 1 <= chunk_bytes <= 8 * 1024 * 1024:
        raise ValueError("Invalid bounded chunk size")
    captured = verify_capture_set(plan, directory, chunk_bytes=chunk_bytes)
    base = Path(directory)
    by_key = {(r["artwork"], r["level"], r["replicate"]): r
              for r in plan["samples"]}
    experiments = {}
    for art in ARTWORKS:
        records = [by_key[(art, level, repeat)] for level, repeat in LEVEL_KEYS]
        outcome = _scan_artwork(records, base, chunk_bytes=chunk_bytes)
        # Preserve reproducibility evidence even when incompatible headers or
        # candidate geometry prevent an interpretable modular comparison.
        identical = captured["same_setting_reexport_and_level_checks"][art][
            "white_50_reexport_byte_identical"]
        if ("white_50_reexport_byte_identical" in outcome and
                outcome["white_50_reexport_byte_identical"] != identical):
            raise ValueError("Payload comparison conflicts with attested whole-file repeatability")
        outcome["white_50_reexport_byte_identical"] = identical
        outcome["repeatability_confounded"] = not identical
        experiments[art] = outcome
    return {
        "schema": "autorip-preregistered-replication-v1",
        "experiment_id": plan["experiment_id"],
        "verified_capture_count": captured["verified_file_count"],
        "locked_candidate": {
            "period_bytes": PERIOD,
            "window_bytes": WINDOW,
            "phase_bytes": PHASE,
            "uniform_reference_share": WINDOW / PERIOD,
            "phase_ambiguity_in_historical_data": True,
        },
        "artworks": experiments,
        "reexport_warnings": captured["warnings"],
        "limitations": [
            "All 12 source PRT hashes were verified against operator-supplied values, not vendor attestations.",
            "Locked parameters were selected using previous three PRTs, not fresh samples.",
            "A byte-mask share is descriptive and not a p-value, ink amount or printer compatibility test.",
            "An unmatched candidate geometry is not automatically evidence that an unknown protocol lacks periodicity.",
            "The historical phase was not uniquely identified; this version reports results for the chosen fixed phase only.",
            "A nonidentical white-50 reexport confounds attribution of byte differences to white-level settings.",
            "Identical 0% and 100% endpoints do not imply an unchanged 50% intermediate.",
            "Repeatability is reported separately even when headers or candidate geometry prevent analysis.",
            "An identical PRT file does not establish printed appearance or physically equal ink deposition.",
            "Metadata checks and repeated SHA-256 scans do not guarantee atomic snapshots on all filesystems.",
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--directory", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    plan = load_plan(args.manifest)
    destination = Path(args.output)
    sources = {((Path(args.directory) / r["filename"]).resolve()) for r in plan["samples"]}
    sources.add(Path(args.manifest).resolve())
    if destination.resolve() in sources:
        raise ValueError("Report cannot overwrite a manifest or PRT source")
    write_new_json(destination, analyze(plan, args.directory))


if __name__ == "__main__":
    main()
