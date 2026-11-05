"""Tests for a non-executing DeviceN text inspector."""
import tempfile
import unittest
from pathlib import Path

from devicen_inspect import DeviceNError, inspect_devicen_text


class DeviceNTests(unittest.TestCase):
    def test_expected_declared_names(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.txt'
            p.write_bytes(b'{{ /DeviceN { /$Cyan /$Magenta /$Yellow /$Black /Spot_1 /Spot_2 /Spot_3 /Spot_4 /Spot_5 /Spot_6 /Spot_7 /Spot_8 } /DeviceCMYK { pop } }}')
            meta=inspect_devicen_text(p)
            self.assertEqual(meta['declared_count'],12)
            self.assertEqual(len(meta['candidate_spots']),8)
            self.assertEqual(meta['raster_mapping'],'unverified')

    def test_non_executing_content_not_evaluated(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.txt'
            p.write_text('/DeviceN { /$Cyan /Spot_1 } (no execution) system')
            self.assertEqual(inspect_devicen_text(p)['declared_names'],['$Cyan','Spot_1'])

    def test_missing_declaration(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.txt';p.write_bytes(b'/DeviceCMYK { pop }')
            with self.assertRaises(DeviceNError):inspect_devicen_text(p)

    def test_safe_size_cap(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.txt';p.write_bytes(b'/DeviceN { /Spot_1 }')
            with self.assertRaises(DeviceNError):inspect_devicen_text(p,max_bytes=2)


if __name__ == '__main__':unittest.main()
