"""Synthetic-only tests; never read proprietary or production PRT bytes."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from verify_sample_hashes import LABELS, verify_sources

class SampleHashTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = {}
        self.reference = {}
        for i, (label, filename) in enumerate(zip(LABELS, ('TESTER1.PRT', 'TESTER1_1.PRT', 'TESTER1_0.PRT'))):
            path = self.root / filename
            data = bytes([i + 1]) * 70 + bytes([100 + i]) * 37
            path.write_bytes(data)
            self.paths[label] = path
            self.reference[label] = {'filename': filename, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

    def verify(self, paths=None, reference=None):
        return verify_sources(paths or self.paths, reference=reference or self.reference)

    def test_valid_sources_produce_original_labelled_manifest(self):
        self.assertEqual(self.verify(), {key: rec['sha256'] for key, rec in self.reference.items()})

    def test_sources_not_modified(self):
        before = {label: self.paths[label].read_bytes() for label in LABELS}
        self.verify()
        self.assertEqual(before, {label: self.paths[label].read_bytes() for label in LABELS})

    def test_tampering_rejected(self):
        data = bytearray(self.paths['white_50'].read_bytes())
        data[-1] ^= 1
        self.paths['white_50'].write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
            self.verify()

    def test_wrong_size_rejected(self):
        self.paths['white_50'].write_bytes(b'different')
        with self.assertRaisesRegex(ValueError, 'Incorrect sample size'):
            self.verify()

    def test_swapped_sources_rejected(self):
        paths = dict(self.paths)
        paths['white_0'], paths['white_100'] = paths['white_100'], paths['white_0']
        with self.assertRaisesRegex(ValueError, 'Unexpected filename'):
            self.verify(paths=paths)

    def test_missing_label_rejected(self):
        paths = dict(self.paths)
        del paths['white_100']
        with self.assertRaisesRegex(ValueError, 'Exactly the three'):
            self.verify(paths=paths)

    def test_source_symlink_rejected(self):
        origin = self.paths['white_0']
        origin.rename(self.root / 'actual.prt')
        try:
            origin.symlink_to(self.root / 'actual.prt')
        except (OSError, NotImplementedError):
            self.skipTest('Symlinks unavailable')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.verify()

    def test_source_hardlink_alias_rejected(self):
        original = self.paths['white_50']
        original.unlink()
        try:
            os.link(self.paths['white_0'], original)
        except (OSError, NotImplementedError):
            self.skipTest('Hardlinks unavailable')
        reference = {label: dict(entry) for label, entry in self.reference.items()}
        reference['white_50']['sha256'] = reference['white_0']['sha256']
        with self.assertRaisesRegex(ValueError, 'Hardlink aliases'):
            self.verify(reference=reference)

    def test_wrong_reference_digest_rejected(self):
        reference = {label: dict(entry) for label, entry in self.reference.items()}
        reference['white_0']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
            self.verify(reference=reference)

if __name__ == '__main__':
    unittest.main()
