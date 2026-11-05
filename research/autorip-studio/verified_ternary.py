"""Read-only ternary analysis requiring independently trusted SHA-256 values."""
import argparse
import json
import os
import stat
from pathlib import Path
from provenance_guard import validate_manifest
from ternary_transition import analyze, LABELS
from safe_json_output import write_new_json

def verified_analyze(paths, expected):
    result = analyze(paths)
    validate_manifest(result["source_sha256"], expected)
    result["provenance_status"] = "matched_external_sha256_manifest"
    return result

def load_sha256_manifest(path: Path):
    """Bounded, descriptor-based read; refuse nonregular and replaced manifests."""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= 4096:
        raise ValueError("Manifest must be a regular JSON file of at most 4096 bytes")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
        if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(before):
            raise ValueError("Manifest changed before opening")
        raw = os.read(fd, 4097)
        after = os.fstat(fd)
        path_after = path.lstat()
        if (identity(after) != identity(opened) or
                identity(path_after) != identity(opened) or
                not stat.S_ISREG(path_after.st_mode) or len(raw) != opened.st_size):
            raise ValueError("Manifest changed while reading")
    finally:
        os.close(fd)
    expected = json.loads(raw.decode("utf-8"))
    validate_manifest(expected, expected)
    return expected

def main():
    parser = argparse.ArgumentParser()
    for label in LABELS:
        parser.add_argument("--" + label.replace("_", "-"), required=True)
    parser.add_argument("--sha256-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    paths = {label: getattr(args, label) for label in LABELS}
    output = Path(args.output)
    manifest = Path(args.sha256_manifest)
    if output.resolve() in {Path(p).resolve() for p in paths.values()} | {manifest.resolve()}:
        raise ValueError("Output cannot replace input")
    expected = load_sha256_manifest(manifest)
    write_new_json(output, verified_analyze(paths, expected))

if __name__ == "__main__":
    main()
