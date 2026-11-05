"""Read-only ternary analysis requiring independently trusted SHA-256 values."""
import argparse
import json
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
    if manifest.is_symlink():
        raise ValueError("Manifest symlinks are not accepted")
    info = manifest.stat()
    if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= 4096:
        raise ValueError("Manifest must be a regular JSON file of at most 4096 bytes")
    with manifest.open("r", encoding="utf-8") as stream:
        expected = json.load(stream)
    write_new_json(output, verified_analyze(paths, expected))

if __name__ == "__main__":
    main()
