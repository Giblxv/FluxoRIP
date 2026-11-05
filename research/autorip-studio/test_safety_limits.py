"""Safety regression tests using only tiny synthetic files."""
import tempfile
import struct
import unittest
from pathlib import Path
from unittest.mock import patch
import layout_hypotheses


class TestSafetyLimits(unittest.TestCase):
    def make(self, *, rows=1, stride=2, slots=12):
        d = tempfile.TemporaryDirectory()
        p = Path(d.name) / 'synthetic.prt'
        h = bytearray(48)
        for off, value in ((0, 0x5555), (12, rows), (16, stride), (28, slots)):
            struct.pack_into('<I', h, off, value)
        p.write_bytes(h + bytes(rows * stride * slots))
        return d, p

    def test_reject_slot_count_above_limit(self):
        d, p = self.make(slots=65)
        with d:
            with self.assertRaisesRegex(ValueError, 'safe bounds'):
                layout_hypotheses.inspect(p)

    def test_reject_stride_above_limit_without_allocation(self):
        d, p = self.make()
        with d:
            data = bytearray(p.read_bytes())
            struct.pack_into('<I', data, 16, 1_000_001)
            p.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'safe bounds'):
                layout_hypotheses.inspect(p)

    def test_reject_file_over_configured_limit(self):
        d, p = self.make()
        with d, patch.object(layout_hypotheses, 'MAX_INPUT_BYTES', 48):
            with self.assertRaisesRegex(ValueError, 'safe size limit'):
                layout_hypotheses.inspect(p)

    def test_original_file_unmodified(self):
        d, p = self.make()
        with d:
            original = p.read_bytes()
            layout_hypotheses.inspect(p)
            self.assertEqual(original, p.read_bytes())


if __name__ == '__main__':
    unittest.main()
