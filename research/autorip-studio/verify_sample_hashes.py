"""Read-only SHA-256 verification of the three labelled FlexiPRINT research samples.

Pinned values came from earlier sample-analysis reports; they are not freshly
attested checksums of the current Google Drive copies. Operator-provided white
percentages are labels, not protocol fields.
"""
from __future__ import annotations
import argparse
import hashlib
import os
import stat
from pathlib import Path

from safe_json_output import write_new_json

LABELS = ('white_0', 'white_50', 'white_100')
REFERENCE = {
    'white_0': {
        'filename': 'TESTER1.PRT',
        'size': 265155120,
        'sha256': '75ef4acb3b7c2dbbce28dc112187ca19b250f2728842eae0c5c7c38b41d8d8ec',
    },
    'white_50': {
        'filename': 'TESTER1_1.PRT',
        'size': 265155120,
        'sha256': '7f5d2036cf9a107a4600f21b3e54a9238850d73861c4de22d8871f3497d68773',
    },
    'white_100': {
        'filename': 'TESTER1_0.PRT',
        'size': 265155120,
        'sha256': 'c143d3bac295c352ec63060ae20f0210c6dbf200e4f18fbee471e96d54c46136',
    },
}

def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)

def _verified_digest(path: Path, expected_bytes: int) -> tuple[str, tuple[int, int]]:
    if path.is_symlink():
        raise ValueError('Source symlink rejected')
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('Source must be a regular file')
    if before.st_size != expected_bytes:
        raise ValueError('Incorrect sample size')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(before):
            raise ValueError('Source changed while opening')
        digest = hashlib.sha256()
        total = 0
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            for chunk in iter(lambda: stream.read(2 * 1024 * 1024), b''):
                digest.update(chunk)
                total += len(chunk)
        after_fd = os.fstat(fd)
        after_path = path.stat(follow_symlinks=False)
        if path.is_symlink() or total != expected_bytes or _identity(opened) != _identity(after_fd) or _identity(opened) != _identity(after_path):
            raise ValueError('Source changed while hashing')
        return digest.hexdigest(), (opened.st_dev, opened.st_ino)
    finally:
        os.close(fd)

def verify_sources(paths, *, reference=REFERENCE) -> dict[str, str]:
    """Return verified labelled hashes usable by verified_ternary.py.

    Reference injection is used only by synthetic tests; CLI pins REFERENCE.
    """
    if not isinstance(paths, dict) or set(paths) != set(LABELS) or set(reference) != set(LABELS):
        raise ValueError('Exactly the three labelled sample sources are required')
    outputs = {}
    seen_paths = set()
    seen_inodes = set()
    for label in LABELS:
        path = Path(paths[label])
        record = reference[label]
        if path.name.casefold() != record['filename'].casefold():
            raise ValueError(f'Unexpected filename for {label}')
        if path.is_symlink():
            raise ValueError(f'Source symlink rejected for {label}')
        resolved = path.resolve(strict=True)
        if resolved in seen_paths:
            raise ValueError('Duplicate source path')
        seen_paths.add(resolved)
        digest, inode = _verified_digest(path, record['size'])
        if inode[1] and inode in seen_inodes:
            raise ValueError('Hardlink aliases are not independent samples')
        seen_inodes.add(inode)
        if digest != record['sha256']:
            raise ValueError(f'Checksum mismatch for {label}')
        outputs[label] = digest
    return outputs

def main() -> None:
    parser = argparse.ArgumentParser(description='Read-only SHA-256 check against historical PRT references')
    for label in LABELS:
        parser.add_argument('--' + label.replace('_', '-'), required=True)
    parser.add_argument('--output', required=True, help='New JSON manifest destination')
    args = parser.parse_args()
    paths = {label: Path(getattr(args, label)) for label in LABELS}
    output = Path(args.output)
    if output.resolve() in {p.resolve() for p in paths.values()}:
        raise ValueError('Output cannot replace an input source')
    if output.is_symlink() or output.exists():
        raise FileExistsError('Manifest output path must not exist')
    write_new_json(output, verify_sources(paths))
    print('OK: source hashes match historical reference values; new manifest written.')

if __name__ == '__main__':
    main()
