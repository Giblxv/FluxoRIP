"""Backwards-compatible PRT inspector tests; only synthetic .bin files."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from prt_readonly import inspect_prt, compare_band_bytes, PRTValidationError


def fixture(path, *, lines=3, stride=4, bands=12, changed=None):
    header = bytearray(48)
    struct.pack_into('<H', header, 0, 0x5555)
    for offset, value in ((12, lines), (16, stride), (28, bands)):
        struct.pack_into('<I', header, offset, value)
    payload = bytearray(lines * bands * stride)
    if changed is not None:
        payload[changed] = 1
    path.write_bytes(header + payload)


class PRTReadOnlyTests(unittest.TestCase):
    def test_signature_geometry_and_sha(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic.bin'; fixture(p)
            info=inspect_prt(p)
            self.assertEqual((info.signature,info.lines,info.stride,info.bands),(0x5555,3,4,12))
            self.assertEqual(info.sha256,hashlib.sha256(p.read_bytes()).hexdigest())

    def test_reject_bad_signature(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.bin'; fixture(p)
            raw=bytearray(p.read_bytes());raw[0]=0;p.write_bytes(raw)
            with self.assertRaises(PRTValidationError):inspect_prt(p)

    def test_reject_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.bin';fixture(p);p.write_bytes(p.read_bytes()[:-1])
            with self.assertRaises(PRTValidationError):inspect_prt(p)

    def test_comparison_row_major(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.bin',Path(d)/'b.bin'
            fixture(a);fixture(b,changed=2*4+1)
            result=compare_band_bytes(a,b,layout='row-major')
            self.assertEqual(result['different_bytes_by_band'][2],1)
            self.assertEqual(result['total_different_bytes'],1)

    def test_comparison_plane_major(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.bin',Path(d)/'b.bin'
            fixture(a);fixture(b,changed=2*3*4+1)
            result=compare_band_bytes(a,b,layout='plane-major')
            self.assertEqual(result['different_bytes_by_band'][2],1)

    def test_no_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.bin',Path(d)/'b.bin'
            fixture(a);fixture(b)
            original=(a.read_bytes(),b.read_bytes());compare_band_bytes(a,b)
            self.assertEqual(original,(a.read_bytes(),b.read_bytes()))

    def test_reject_small_custom_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.bin';fixture(p)
            with self.assertRaises(PRTValidationError): inspect_prt(p,max_bytes=48)

    def test_reject_mismatched_geometries(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.bin',Path(d)/'b.bin';fixture(a);fixture(b,lines=4)
            with self.assertRaises(PRTValidationError):compare_band_bytes(a,b)


if __name__=='__main__': unittest.main()
