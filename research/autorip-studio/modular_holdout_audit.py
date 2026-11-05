"""Read-only, aggregate-only modular change-mask holdout experiment.

This tests recurrence at the *candidate* period (lines * bands) rather than
assuming printer channels, white dosage, pixel structure, or ink semantics.

The selected window is fit on the first half of the 0%-versus-100% operator-
labelled sample and evaluated on a disjoint second-half segment. Period and
window sizes are inherited from prior research; not independently discovered.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import stat
import struct

import numpy as np

from provenance_guard import validate_manifest
from safe_json_output import write_new_json
from verify_sample_hashes import LABELS, REFERENCE, verify_sources

HEADER_BYTES = 48
BANDS = 12
PAIRS = (("0_vs_50", 0, 1), ("50_vs_100", 1, 2), ("0_vs_100", 0, 2))


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _circular_window_counts(counts: np.ndarray, width: int) -> np.ndarray:
    period = len(counts)
    if not 1 <= width <= period:
        raise ValueError("Invalid circular-window width")
    extended = np.concatenate((counts, counts[:width-1]))
    prefix = np.concatenate((np.zeros(1, dtype=np.int64), np.cumsum(extended, dtype=np.int64)))
    return prefix[width:width + period] - prefix[:period]


def _best_window(counts: np.ndarray, width: int) -> tuple[int, int]:
    window_counts = _circular_window_counts(counts, width)
    phase = int(np.argmax(window_counts))  # deterministic earliest tie
    return phase, int(window_counts[phase])


def _optimal_phase_count(counts: np.ndarray, width: int) -> int:
    windows = _circular_window_counts(counts, width)
    return int(np.count_nonzero(windows == windows.max()))


def _at_phase(counts: np.ndarray, width: int, phase: int) -> int:
    period = len(counts)
    if not 0 <= phase < period:
        raise ValueError("Phase outside modular period")
    end = phase + width
    if end <= period:
        return int(counts[phase:end].sum())
    return int(counts[phase:].sum() + counts[:end - period].sum())


def analyze(paths, *, reference=REFERENCE, chunk_bytes=1024*1024):
    if not 1 <= chunk_bytes <= 16 * 1024 * 1024:
        raise ValueError("Invalid bounded chunk size")
    if set(paths) != set(LABELS):
        raise ValueError("Three operator-labelled paths required")
    if set(reference) != set(LABELS):
        raise ValueError("Three reference records required")
    expected = {label: reference[label]["sha256"] for label in LABELS}
    validate_manifest(expected, expected)
    verify_sources(paths, reference=reference)

    paths = [Path(paths[label]) for label in LABELS]
    pre = [path.lstat() for path in paths]
    if any(not stat.S_ISREG(i.st_mode) for i in pre):
        raise ValueError("Only regular files accepted")
    if len({(i.st_dev, i.st_ino) for i in pre}) != 3:
        raise ValueError("Distinct source inodes required")

    fds = []
    streams = []
    digests = [hashlib.sha256() for _ in paths]
    try:
        for path, before in zip(paths, pre):
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
            fds.append(fd)
            if _identity(os.fstat(fd)) != _identity(before):
                raise ValueError("Source changed while opening")
            streams.append(os.fdopen(fd, "rb", closefd=False))
        headers = [stream.read(HEADER_BYTES) for stream in streams]
        if len(set(headers)) != 1 or len(headers[0]) != HEADER_BYTES:
            raise ValueError("Source headers are not identical")
        if struct.unpack_from("<H", headers[0], 0)[0] != 0x5555:
            raise ValueError("Candidate PRT signature missing")
        for digest, header in zip(digests, headers):
            digest.update(header)
        lines, stride, bands = (struct.unpack_from("<I", headers[0], pos)[0] for pos in (12, 16, 28))
        if not (1 <= lines <= 1_000_000 and 2 <= stride <= 1_000_000 and bands == BANDS):
            raise ValueError("Invalid candidate geometry")
        period = lines * bands
        if period > 3_000_000 or HEADER_BYTES + period * stride != pre[0].st_size or any(p.st_size != pre[0].st_size for p in pre):
            raise ValueError("Geometry inconsistent with source sizes")
        payload_bytes = period * stride
        train_bytes = period * (stride // 2)
        hist = {pair: (np.zeros(period, dtype=np.int64), np.zeros(period, dtype=np.int64))
                for pair, _, _ in PAIRS}
        for offset in range(0, payload_bytes, chunk_bytes):
            size = min(chunk_bytes, payload_bytes - offset)
            blocks = [stream.read(size) for stream in streams]
            if any(len(block) != size for block in blocks):
                raise ValueError("Source truncated")
            for digest, block in zip(digests, blocks):
                digest.update(block)
            arrays = [np.frombuffer(b, dtype=np.uint8) for b in blocks]
            for pair, i, j in PAIRS:
                changed = np.flatnonzero(arrays[i] != arrays[j])
                if not changed.size:
                    continue
                position = changed.astype(np.int64) + offset
                boundary = int(np.searchsorted(position, train_bytes, side="left"))
                for half, selection in enumerate((position[:boundary], position[boundary:])):
                    if selection.size:
                        hist[pair][half][:] += np.bincount(selection % period, minlength=period).astype(np.int64)
        if any(stream.read(1) for stream in streams):
            raise ValueError("Source grew during analysis")
        for path, fd, before in zip(paths, fds, pre):
            if _identity(os.fstat(fd)) != _identity(before) or _identity(path.lstat()) != _identity(before):
                raise ValueError("Source changed during analysis")
        actual = dict(zip(LABELS, (digest.hexdigest() for digest in digests)))
        validate_manifest(actual, expected)
    finally:
        for stream in streams:
            stream.close()
        for fd in fds:
            os.close(fd)

    # The phase is fitted *only* from the 0-vs-100 training half.
    phase, _ = _best_window(hist["0_vs_100"][0], lines)
    pairs = {}
    for name, _, _ in PAIRS:
        halves = []
        for half in (0, 1):
            counts = hist[name][half]
            total = int(counts.sum())
            inside = _at_phase(counts, lines, phase)
            best_phase, best_count = _best_window(counts, lines)
            halves.append({
                "half": "training" if half == 0 else "holdout",
                "changed_bytes": total,
                "inside_fixed_training_window": inside,
                "outside_fixed_training_window": total - inside,
                "fixed_window_share": (inside / total if total else None),
                "best_phase_descriptive_only": best_phase,
                "best_window_changed_bytes": best_count,
                "equally_optimal_phase_count": _optimal_phase_count(counts, lines),
            })
        pairs[name] = halves

    alternatives = []
    base = hist["0_vs_100"][0]
    for divisor in (2, 4, 8, 16):
        if period % divisor or lines % divisor:
            continue
        shorter = period // divisor
        folded = base.reshape(divisor, shorter).sum(axis=0)
        shorter_phase, shorter_inside = _best_window(folded, lines // divisor)
        total = int(base.sum())
        alternatives.append({"relative_period": f"1/{divisor}",
                             "period_bytes": shorter,
                             "window_bytes": lines // divisor,
                             "best_train_phase": shorter_phase,
                             "best_train_share": shorter_inside / total if total else None})

    return {
        "schema": "autorip-modular-holdout-v1",
        "labels": list(LABELS),
        "reference_provenance": "pinned historical digests, verified before and during scan",
        "source_sha256": actual,
        "candidate_period_bytes": period,
        "candidate_window_bytes": lines,
        "training_window_phase": phase,
        "training_equally_optimal_phase_count": _optimal_phase_count(hist["0_vs_100"][0], lines),
        "training_payload_bytes": train_bytes,
        "holdout_payload_bytes": payload_bytes - train_bytes,
        "pairwise": pairs,
        "candidate_shorter_periods": alternatives,
        "limitations": [
            "Period and window were suggested by prior analyses of these same samples; holdout does not constitute an independent dataset.",
            "Concentration and apparent periodicity do not establish printer protocol semantics, physical ink channels, or 2-bit pixels.",
            "0/50/100 values are operator-supplied labels rather than measured white ink coverage.",
            "Hashes and stat comparisons cannot guarantee atomic snapshots against all concurrent writers.",
            "Only aggregate derived counts are emitted; original payload bytes are never exported.",
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for label in LABELS:
        ap.add_argument("--" + label.replace("_", "-"), required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    paths = {name: Path(getattr(args, name)) for name in LABELS}
    output = Path(args.output)
    if output.resolve() in {p.resolve() for p in paths.values()}:
        raise ValueError("Cannot replace a source with aggregate output")
    write_new_json(output, analyze(paths))
    print("Wrote aggregate, read-only modular holdout report to", output)


if __name__ == "__main__":
    main()
