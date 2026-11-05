import tempfile, unittest, struct
from pathlib import Path
from spatial_layout import compare_layouts

class SpatialTests(unittest.TestCase):
    def fixture(self, root, *, layout='row_major', rows=7, slots=12, stride=9, truncate=0):
        header=struct.pack('<12I',0x5555,0,0,rows,stride,0,0,slots,0,0,0,0)
        data=bytearray(rows*slots*stride)
        for row in range(rows):
            for slot in range(slots):
                pos=((row*slots+slot) if layout=='row_major' else (slot*rows+row))*stride
                data[pos:pos+stride]=bytes([(slot*17+row//3)%256])*stride
        path=root/'sample.prt';path.write_bytes(header+data[:len(data)-truncate]);return path
    def test_both_layouts_report(self):
        with tempfile.TemporaryDirectory() as d:
            x=compare_layouts(self.fixture(Path(d)))
            self.assertEqual(set(x['hypotheses']),{'row_major','plane_major'})
            self.assertEqual(x['conclusion'],'undetermined')
    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(Path(d));self.assertEqual(compare_layouts(p),compare_layouts(p))
    def test_sampling_bound(self):
        with tempfile.TemporaryDirectory() as d:
            x=compare_layouts(self.fixture(Path(d)),max_pairs=5,sample_bytes=4)
            self.assertEqual(x['hypotheses']['row_major']['compared_bytes'],20)
    def test_stride_cap(self):
        with tempfile.TemporaryDirectory() as d:
            x=compare_layouts(self.fixture(Path(d)),max_pairs=3,sample_bytes=100)
            self.assertEqual(x['hypotheses']['row_major']['bytes_per_pair'],9)
    def test_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):compare_layouts(self.fixture(Path(d),truncate=1))
    def test_bad_limits(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(Path(d))
            for opts in ({'max_pairs':0},{'sample_bytes':0}):
                with self.assertRaises(ValueError):compare_layouts(p,**opts)
    def test_single_row(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):compare_layouts(self.fixture(Path(d),rows=1))
    def test_realistic_plane(self):
        with tempfile.TemporaryDirectory() as d:
            x=compare_layouts(self.fixture(Path(d),layout='plane_major'))
            self.assertLess(x['hypotheses']['plane_major']['different_fraction'],x['hypotheses']['row_major']['different_fraction'])

if __name__=='__main__':unittest.main()
