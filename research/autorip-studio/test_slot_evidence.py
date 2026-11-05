import struct
import tempfile
import unittest
from pathlib import Path
from slot_evidence import compare_slots


def make_prt(p, rows=5, slots=12, stride=4):
    fields=[0x5555,0,0,rows,stride,0,0,slots,0,0,0,0]
    p.write_bytes(struct.pack('<12I',*fields)+bytes((i*17)%256 for i in range(rows*slots*stride)))

class TestSlotEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'sample.prt';make_prt(self.path)
    def test_each_slot(self):
        x=compare_slots(self.path,pairs_per_slot=2)
        for mode in ('row_major','plane_major'):
            self.assertEqual(len(x['hypotheses'][mode]),12)
            self.assertEqual([s['slot_index'] for s in x['hypotheses'][mode]],list(range(12)))
            self.assertTrue(all(s['compared_bytes']==8 for s in x['hypotheses'][mode]))
    def test_deterministic(self):
        self.assertEqual(compare_slots(self.path),compare_slots(self.path))
    def test_original_unchanged(self):
        before=self.path.read_bytes();compare_slots(self.path);self.assertEqual(self.path.read_bytes(),before)
    def test_limits(self):
        with self.assertRaises(ValueError):compare_slots(self.path,pairs_per_slot=0)
        with self.assertRaises(ValueError):compare_slots(self.path,sample_bytes=0)
    def test_clamp(self):
        x=compare_slots(self.path,pairs_per_slot=100,sample_bytes=100)
        self.assertEqual(len(x['sample_rows']),4);self.assertEqual(x['bytes_per_pair'],4)
    def test_truncated(self):
        self.path.write_bytes(self.path.read_bytes()[:-1])
        with self.assertRaises(ValueError):compare_slots(self.path)
    def test_invalid_signature(self):
        b=bytearray(self.path.read_bytes());b[0]=0;self.path.write_bytes(b)
        with self.assertRaises(ValueError):compare_slots(self.path)
    def test_single_row(self):
        make_prt(self.path,rows=1)
        with self.assertRaises(ValueError):compare_slots(self.path)

if __name__=='__main__':unittest.main()
