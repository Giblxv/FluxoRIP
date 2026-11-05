import hashlib
import tempfile
import unittest
from pathlib import Path
from provenance_guard import LABELS, sha256_file, validate_manifest

class ProvenanceGuardTests(unittest.TestCase):
    def setUp(self):
        self.data = {label: hashlib.sha256(label.encode()).hexdigest() for label in LABELS}

    def test_valid_manifest(self):
        validate_manifest(self.data, dict(self.data))

    def test_mismatch(self):
        altered = dict(self.data)
        altered['white_0'] = '0' * 64
        with self.assertRaises(ValueError): validate_manifest(altered, self.data)

    def test_swapped_labels(self):
        altered = dict(self.data)
        altered['white_50'], altered['white_100'] = altered['white_100'], altered['white_50']
        with self.assertRaises(ValueError): validate_manifest(altered, self.data)

    def test_missing_label(self):
        with self.assertRaises(ValueError): validate_manifest({'white_0': self.data['white_0']}, self.data)

    def test_extra_label(self):
        altered = dict(self.data, extra='f'*64)
        with self.assertRaises(ValueError): validate_manifest(altered, self.data)

    def test_invalid_digest(self):
        altered = dict(self.data, white_0='A'*64)
        with self.assertRaises(ValueError): validate_manifest(altered, self.data)

    def test_hash_chunk_invariance_and_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'sample.bin'
            content = bytes(range(256))*37
            p.write_bytes(content)
            before = p.stat()
            expected = hashlib.sha256(content).hexdigest()
            self.assertEqual(sha256_file(p, chunk_bytes=1), expected)
            self.assertEqual(sha256_file(p, chunk_bytes=1024), expected)
            after = p.stat()
            self.assertEqual((before.st_size, before.st_mtime_ns), (after.st_size, after.st_mtime_ns))

    def test_invalid_chunk(self):
        with self.assertRaises(ValueError): sha256_file('unused', chunk_bytes=0)

if __name__ == '__main__': unittest.main()
