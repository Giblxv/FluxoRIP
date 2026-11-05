"""Validate labelled SHA-256 evidence before attributing analysis results."""
from __future__ import annotations
import hashlib
import hmac
import re
from pathlib import Path

LABELS = ('white_0', 'white_50', 'white_100')
_SHA256 = re.compile(r'[0-9a-f]{64}\Z')

def validate_manifest(actual: dict[str, str], expected: dict[str, str]) -> None:
    """Reject missing, unexpected, malformed or mismatched labelled digests."""
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        raise ValueError('SHA-256 manifests must be dictionaries')
    if set(actual) != set(LABELS) or set(expected) != set(LABELS):
        raise ValueError('Exactly three labelled SHA-256 digests required')
    for label in LABELS:
        a, e = actual[label], expected[label]
        if not isinstance(a, str) or not isinstance(e, str) or not _SHA256.fullmatch(a) or not _SHA256.fullmatch(e):
            raise ValueError(f'Invalid SHA-256 for {label}')
        if not hmac.compare_digest(a, e):
            raise ValueError(f'SHA-256 mismatch for {label}')

def sha256_file(path: str | Path, *, chunk_bytes: int = 1024 * 1024) -> str:
    if not 1 <= chunk_bytes <= 8 * 1024 * 1024:
        raise ValueError('Invalid chunk size')
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(chunk_bytes), b''):
            digest.update(chunk)
    return digest.hexdigest()
