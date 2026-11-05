"""Offline, read-only intake of *new* independent controlled PRT experiments.

This module does NOT generate or print PRT, command PrintExp/Hoson, decode ink
channels, or infer any vendor semantics. A previously obtained operator-attested
hash is required for each of twelve input samples. The artwork and configuration
hashes are operator-supplied metadata, not recomputed by this intake.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from safe_json_output import write_new_json

SCHEMA = "autorip-controlled-capture-v1"
ARTWORKS = ("art_a", "art_b", "art_c")
LEVELS = ("white_0", "white_50", "white_100")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.PRT\Z", re.IGNORECASE)
EXPERIMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,63}\Z")
SAMPLE_FIELDS = {"artwork", "level", "replicate", "filename", "size_bytes", "sha256"}
EXPECTED = {(a, level, 1) for a in ARTWORKS for level in LEVELS} | {
    (a, "white_50", 2) for a in ARTWORKS
}


def template(experiment_id="pilot_001"):
    if not isinstance(experiment_id, str) or not EXPERIMENT.fullmatch(experiment_id):
        raise ValueError("Experiment ID must be 3..64 safe characters")
    return {
        "schema": SCHEMA,
        "experiment_id": experiment_id,
        "common_config_sha256": "",
        "artworks": {a: "" for a in ARTWORKS},
        "samples": [
            {"artwork": a, "level": level, "replicate": replicate,
             "filename": f"{a}_{level}_r{replicate}.PRT",
             "size_bytes": None, "sha256": ""}
            for a, level, replicate in sorted(EXPECTED)
        ],
    }


def _valid_digest(value):
    return (isinstance(value, str) and DIGEST.fullmatch(value) is not None
            and value != "0" * 64)


def validate_plan(plan):
    if not isinstance(plan, dict) or set(plan) != {
        "schema", "experiment_id", "common_config_sha256", "artworks", "samples"
    }:
        raise ValueError("Invalid capture plan structure")
    if plan["schema"] != SCHEMA:
        raise ValueError("Unsupported capture plan schema")
    if not isinstance(plan["experiment_id"], str) or not EXPERIMENT.fullmatch(plan["experiment_id"]):
        raise ValueError("Invalid experiment identifier")
    if not _valid_digest(plan["common_config_sha256"]):
        raise ValueError("Missing operator-supplied common configuration SHA-256")
    artworks = plan["artworks"]
    if not isinstance(artworks, dict) or set(artworks) != set(ARTWORKS):
        raise ValueError("Exactly three distinct artwork IDs required")
    if any(not _valid_digest(v) for v in artworks.values()) or len(set(artworks.values())) != 3:
        raise ValueError("Artwork source SHA-256s must be valid and distinct")
    samples = plan["samples"]
    if not isinstance(samples, list) or len(samples) != len(EXPECTED):
        raise ValueError("Exactly twelve controlled captures required")
    observed = set()
    file_names = set()
    for sample in samples:
        if not isinstance(sample, dict) or set(sample) != SAMPLE_FIELDS:
            raise ValueError("Unexpected capture record structure")
        if (type(sample["artwork"]) is not str or
                type(sample["level"]) is not str or
                type(sample["replicate"]) is not int):
            raise ValueError("Artwork/level/replicate identifiers must use exact types")
        triple = (sample["artwork"], sample["level"], sample["replicate"])
        if triple not in EXPECTED or triple in observed:
            raise ValueError("Unexpected or repeated artwork/white/replicate condition")
        observed.add(triple)
        filename = sample["filename"]
        if not isinstance(filename, str) or not FILENAME.fullmatch(filename):
            raise ValueError("Unsafe capture filename (must be plain .PRT basename)")
        if filename.casefold() in file_names:
            raise ValueError("Repeated PRT filename")
        expected_name = f"{sample['artwork']}_{sample['level']}_r{sample['replicate']}.PRT"
        if filename.casefold() != expected_name.casefold():
            raise ValueError("PRT filename does not match declared capture condition")
        file_names.add(filename.casefold())
        if (type(sample["size_bytes"]) is not int or
                not 48 <= sample["size_bytes"] <= 1024**4):
            raise ValueError("Invalid expected PRT size")
        if not _valid_digest(sample["sha256"]):
            raise ValueError("Missing or malformed independent capture SHA-256")
    if observed != EXPECTED:
        raise ValueError("Missing artwork/white/replicate conditions")
    return plan


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key in manifest")
        result[key] = value
    return result


def load_plan(path):
    source = Path(path)
    before = source.lstat()
    if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= 65536:
        raise ValueError("Plan must be a regular JSON file of 1..65536 bytes")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(source, flags)
    try:
        opened = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
        if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(before):
            raise ValueError("Plan changed before opening")
        raw = os.read(fd, 65537)
        after = os.fstat(fd)
        post_path = source.lstat()
        if (identity(after) != identity(opened) or
                identity(post_path) != identity(opened) or
                not stat.S_ISREG(post_path.st_mode) or
                len(raw) != opened.st_size):
            raise ValueError("Plan changed during read")
    finally:
        os.close(fd)
    return validate_plan(json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys))


def _file_identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _verify_capture(path, size, expected_hash, *, chunk_bytes=2 * 1024 * 1024):
    if path.is_symlink():
        raise ValueError("Capture symlinks are forbidden")
    pre = path.lstat()
    if not stat.S_ISREG(pre.st_mode) or pre.st_size != size:
        raise ValueError("Capture not a regular file or expected size mismatch")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if _file_identity(opened) != _file_identity(pre):
            raise ValueError("Capture changed while opening")
        digest = hashlib.sha256()
        total = 0
        while True:
            block = os.read(fd, chunk_bytes)
            if not block:
                break
            total += len(block)
            digest.update(block)
        after_fd = os.fstat(fd)
        after_path = path.lstat()
        if (not stat.S_ISREG(after_path.st_mode) or
                _file_identity(opened) != _file_identity(after_fd) or
                _file_identity(opened) != _file_identity(after_path) or total != size):
            raise ValueError("Capture changed during scan")
        actual = digest.hexdigest()
        if actual != expected_hash:
            raise ValueError("Capture SHA-256 mismatch")
        return actual, (opened.st_dev, opened.st_ino)
    finally:
        os.close(fd)


def verify_capture_set(plan, directory, *, chunk_bytes=2 * 1024 * 1024):
    """Verify pre-attested captured bytes; never create or write printer artifacts.

    Different hashes for same-condition reruns are captured as a reproducibility
    warning, NOT asserted to prove ink effects or protocol layout.
    """
    validate_plan(plan)
    if type(chunk_bytes) is not int or not 1 <= chunk_bytes <= 8 * 1024 * 1024:
        raise ValueError("Invalid bounded chunk size")
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Capture directory must exist and not be a symlink")
    seen_inodes = set()
    data = {}
    total_bytes = 0
    for sample in plan["samples"]:
        key = (sample["artwork"], sample["level"], sample["replicate"])
        sha, inode = _verify_capture(
            root / sample["filename"], sample["size_bytes"], sample["sha256"],
            chunk_bytes=chunk_bytes)
        if inode in seen_inodes:
            raise ValueError("A hardlink alias cannot count as independent capture")
        seen_inodes.add(inode)
        data[key] = sha
        total_bytes += sample["size_bytes"]
    checks = {}
    warnings = []
    for art in ARTWORKS:
        rerip_same = data[(art, "white_50", 1)] == data[(art, "white_50", 2)]
        levels_equal = {
            "0_equals_50": data[(art, "white_0", 1)] == data[(art, "white_50", 1)],
            "50_equals_100": data[(art, "white_50", 1)] == data[(art, "white_100", 1)],
            "0_equals_100": data[(art, "white_0", 1)] == data[(art, "white_100", 1)],
        }
        checks[art] = {
            "white_50_reexport_byte_identical": rerip_same,
            "level_pairwise_byte_identical": levels_equal,
        }
        if not rerip_same:
            warnings.append(f"{art}: identical operator settings did not reproduce identical bytes")
        if any(levels_equal.values()):
            warnings.append(f"{art}: one or more declared white levels generated identical bytes")
    # Deliberately do not publish operator-provided artwork source fingerprints.
    return {
        "schema": "autorip-controlled-capture-verification-v1",
        "experiment_id": plan["experiment_id"],
        "verified_file_count": len(data),
        "verified_total_bytes": total_bytes,
        "sha256_agrees_with_operator_supplied_manifest": True,
        "same_setting_reexport_and_level_checks": checks,
        "warnings": warnings,
        "limitations": [
            "Artwork SHA-256 and common RIP configuration fingerprint are operator claims, not independently verified here.",
            "Matching sample SHA-256 values proves agreement with the supplied manifest, not vendor authenticity.",
            "Equal bytes do not establish identical printed output; unequal bytes do not establish an ink coverage difference.",
            "New artwork replicates must be generated independently from the historical three-sample experiment.",
            "No proprietary sample bytes or printer instructions are exported.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    gen = commands.add_parser("template", help="Create a new unfilled capture plan")
    gen.add_argument("--experiment-id", default="pilot_001")
    gen.add_argument("--output", required=True)
    verify = commands.add_parser("verify", help="Verify a 12-sample capture using an externally filled plan")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--directory", required=True)
    verify.add_argument("--output", required=True)
    args = parser.parse_args()
    out = Path(args.output)
    if args.command == "template":
        write_new_json(out, template(args.experiment_id))
        print("Created a NEW unfilled plan; do not treat placeholders as verified.")
        return
    manifest = Path(args.manifest)
    if out.resolve() == manifest.resolve():
        raise ValueError("Output cannot replace capture plan")
    plan = load_plan(manifest)
    inputs = {(Path(args.directory) / x["filename"]).resolve() for x in plan["samples"]}
    if out.resolve() in inputs:
        raise ValueError("Output cannot replace capture inputs")
    result = verify_capture_set(plan, args.directory)
    write_new_json(out, result)
    print("Verified", result["verified_file_count"], "operator-labelled captures.")


if __name__ == "__main__":
    main()
