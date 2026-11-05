import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from icc_inspect import inspect_icc, ICCError

def sample(path, cs=b'CMYK', tags=()):
    blob = bytearray(132+12*len(tags))
    struct.pack_into('>I', blob, 0, len(blob))
    blob[8] = 4
    blob[12:16] = b'prtr'
    blob[16:20] = cs
    blob[20:24] = b'Lab '
    blob[36:40] = b'acsp'
    struct.pack_into('>I', blob, 128, len(tags))
    for i, (sig, off, size) in enumerate(tags):
        pos = 132 + 12*i
        blob[pos:pos+4] = sig
        struct.pack_into('>II', blob, pos+4, off, size)
    path.write_bytes(blob)

class ICCTests(unittest.TestCase):
    def test_cmyk(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'a.icc'; sample(p)
            r=inspect_icc(p)
            self.assertEqual(r['channel_count_candidate'],4)
            self.assertEqual(r['sha256'],hashlib.sha256(p.read_bytes()).hexdigest())
    def test_five_channels_candidate_not_white(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.icc';sample(p,b'5CLR')
            self.assertEqual(inspect_icc(p)['channel_count_candidate'],5)
            self.assertIn('does not prove',inspect_icc(p)['warning'])
    def test_reject_bad_magic(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.icc';sample(p); b=bytearray(p.read_bytes());b[36]=0;p.write_bytes(b)
            with self.assertRaises(ICCError): inspect_icc(p)
    def test_reject_bad_size(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.icc';sample(p);p.write_bytes(p.read_bytes()+b'x')
            with self.assertRaises(ICCError): inspect_icc(p)
    def test_reject_out_of_bounds_tag(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.icc';sample(p,tags=((b'desc',999,20),))
            with self.assertRaises(ICCError): inspect_icc(p)
    def test_reject_truncated_directory(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.icc';sample(p);b=bytearray(p.read_bytes());struct.pack_into('>I',b,128,1);p.write_bytes(b)
            with self.assertRaises(ICCError): inspect_icc(p)
if __name__=='__main__':unittest.main()
