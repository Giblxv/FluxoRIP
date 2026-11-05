"""Synthetic-only regression tests for verified ternary analysis."""
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

from verified_ternary import verified_analyze

LABELS = ("white_0", "white_50", "white_100")


class VerifiedTernaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.paths = {}
        self.expected = {}
        for i, label in enumerate(LABELS):
            path = Path(self.temp.name) / (label + ".fixture")
            header = bytearray(48)
            struct.pack_into("<H", header, 0, 0x5555)
            struct.pack_into("<I", header, 12, 1)
            struct.pack_into("<I", header, 16, 4)
            struct.pack_into("<I", header, 28, 12)
            data = header + bytes([i, 0, 0, 0] * 12)
            path.write_bytes(data)
            self.paths[label] = path
            self.expected[label] = hashlib.sha256(data).hexdigest()

    def test_matching_manifest(self):
        result = verified_analyze(self.paths, self.expected)
        self.assertEqual(result["provenance_status"], "matched_external_sha256_manifest")

    def test_wrong_digest_rejected(self):
        bad = dict(self.expected)
        bad["white_50"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "mismatch"):
            verified_analyze(self.paths, bad)

    def test_swapped_labels_rejected(self):
        bad = dict(self.expected)
        bad["white_0"], bad["white_100"] = bad["white_100"], bad["white_0"]
        with self.assertRaisesRegex(ValueError, "mismatch"):
            verified_analyze(self.paths, bad)

    def test_missing_label_rejected(self):
        bad = dict(self.expected)
        del bad["white_50"]
        with self.assertRaisesRegex(ValueError, "Exactly three"):
            verified_analyze(self.paths, bad)

    def test_modified_payload_rejected(self):
        path = self.paths["white_50"]
        data = bytearray(path.read_bytes())
        data[-1] ^= 1
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "mismatch"):
            verified_analyze(self.paths, self.expected)


if __name__ == "__main__":
    unittest.main()
