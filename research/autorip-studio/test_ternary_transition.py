"""Synthetic-only regression tests: fixtures are not production PRTs."""
from pathlib import Path
import hashlib
import os
import struct
import tempfile
import unittest
from ternary_transition import analyze


def fixture(path, payload, lines=1, stride=5, bands=12):
    header = bytearray(48)
    struct.pack_into('<H', header, 0, 0x5555)
    for offset, value in ((12, lines), (16, stride), (28, bands)):
        struct.pack_into('<I', header, offset, value)
    path.write_bytes(header + bytes(payload))


class TernaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.paths = {k: Path(self.tmp.name) / (k + '.fixture') for k in ('white_0', 'white_50', 'white_100')}
        # First 5 bytes represent all five classes, remaining 55 bytes equal.
        samples = ((0, 1, 1, 1, 1), (0, 1, 2, 3, 2), (0, 2, 1, 3, 3))
        for k, head in zip(self.paths, samples):
            fixture(self.paths[k], head + (0,) * 55)

    def test_all_five_classes_and_pairwise_counts(self):
        r = analyze(self.paths, chunk_bytes=2)
        self.assertEqual(r['counts_by_candidate_plane'][0], dict(zip(
            ('all_equal', 'zero_equals_fifty', 'zero_equals_hundred', 'fifty_equals_hundred', 'all_distinct'),
            (1, 1, 1, 1, 1))))
        self.assertEqual(r['totals']['all_equal'], 56)
        self.assertEqual(r['derived_pairwise_changed_byte_counts'],
                         {'0_vs_50': 3, '50_vs_100': 3, '0_vs_100': 3})

    def test_chunk_invariance(self):
        a = analyze(self.paths, chunk_bytes=1)
        b = analyze(self.paths, chunk_bytes=60)
        self.assertEqual(a, b)

    def test_source_sha256_and_preservation(self):
        before = {k: p.read_bytes() for k, p in self.paths.items()}
        r = analyze(self.paths)
        self.assertEqual(r['source_sha256'], {k: hashlib.sha256(v).hexdigest() for k, v in before.items()})
        self.assertEqual(before, {k: p.read_bytes() for k, p in self.paths.items()})

    def test_header_mismatch(self):
        p = self.paths['white_100']
        data = bytearray(p.read_bytes()); data[35] = 1; p.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'headers'):
            analyze(self.paths)

    def test_geometry_mismatch(self):
        p = self.paths['white_100']
        data = bytearray(p.read_bytes()); struct.pack_into('<I', data, 16, 6); p.write_bytes(data)
        with self.assertRaises(ValueError):
            analyze(self.paths)

    def test_source_hardlink_alias_rejected(self):
        alias = Path(self.tmp.name) / 'alias'
        os.link(self.paths['white_0'], alias)
        paths = dict(self.paths); paths['white_50'] = alias
        with self.assertRaisesRegex(ValueError, 'inodes'):
            analyze(paths)

    def test_source_symlink_rejected(self):
        alias = Path(self.tmp.name) / 'alias'
        try:
            alias.symlink_to(self.paths['white_0'])
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        paths = dict(self.paths); paths['white_0'] = alias
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            analyze(paths)

    def test_invalid_chunk_rejected(self):
        with self.assertRaisesRegex(ValueError, 'chunk_bytes'):
            analyze(self.paths, chunk_bytes=0)

    def test_missing_label_rejected(self):
        with self.assertRaisesRegex(ValueError, 'labelled'):
            analyze({'white_0': self.paths['white_0']})

    def test_invalid_signature_rejected(self):
        p = self.paths['white_0']
        data = bytearray(p.read_bytes()); data[0] = 0; p.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'signature'):
            analyze(self.paths)


if __name__ == '__main__':
    unittest.main()