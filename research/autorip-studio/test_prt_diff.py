import tempfile, unittest, struct
from pathlib import Path
from prt_diff import compare


def fixture(path, rows=3, slots=2, stride=5, edits=()):
    header=list(range(12)); header[0]=0x5555;header[3]=rows;header[4]=stride;header[7]=slots
    data=bytearray(struct.pack('<12I',*header)+bytes(rows*slots*stride))
    for offset,value in edits: data[offset]=value
    Path(path).write_bytes(data)

class TestDiff(unittest.TestCase):
    def test_one_byte_both_layouts(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=Path(t)/'a',Path(t)/'b';fixture(a);fixture(b,edits=[(48+5,9)])
            result=compare(a,b,block_size=2)
            for name in ('row_major','plane_major'):
                self.assertEqual(sum(x['different_bytes'] for x in result['hypotheses'][name]),1)
            self.assertEqual(result['hypotheses']['row_major'][1]['first_difference']['row'],0)
            self.assertEqual(result['hypotheses']['plane_major'][0]['first_difference']['row'],1)
    def test_identical(self):
        with tempfile.TemporaryDirectory() as t:
            a=Path(t)/'a';fixture(a); r=compare(a,a)
            self.assertTrue(r['same_content'])
            self.assertTrue(all(x['different_bytes']==0 for v in r['hypotheses'].values() for x in v))
    def test_geometry_mismatch(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=Path(t)/'a',Path(t)/'b';fixture(a);fixture(b,rows=4)
            with self.assertRaisesRegex(ValueError,'incompatible'): compare(a,b)
    def test_invalid_block_size(self):
        with self.assertRaises(ValueError): compare('a','b',block_size=0)
    def test_header_change_not_raster(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=Path(t)/'a',Path(t)/'b';fixture(a);fixture(b)
            raw=bytearray(b.read_bytes());raw[4]=99;b.write_bytes(raw)
            r=compare(a,b)
            self.assertFalse(r['header_equal'])
            self.assertTrue(all(x['different_bytes']==0 for v in r['hypotheses'].values() for x in v))
    def test_first_difference_absolute_offset(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=Path(t)/'a',Path(t)/'b';fixture(a);fixture(b,edits=[(48+29,1)])
            r=compare(a,b,block_size=1)
            for v in r['hypotheses'].values():
                d=[x['first_difference'] for x in v if x['first_difference']]
                self.assertEqual(d[0]['absolute_offset'],77)

if __name__=='__main__':unittest.main()

class TestDiffBoundaries(unittest.TestCase):
    def test_many_changes_crossing_chunks(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=Path(t)/'a',Path(t)/'b'
            fixture(a,rows=5,slots=3,stride=7)
            positions=[0,6,7,20,21,34,35,69,104]
            fixture(b,rows=5,slots=3,stride=7,edits=[(48+i,1) for i in positions])
            for block in (1,2,3,7,8,16,1024):
                r=compare(a,b,block_size=block)
                self.assertEqual(r['header_changed_offsets'],[])
                for layout in ('row_major','plane_major'):
                    counts=r['hypotheses'][layout]
                    self.assertEqual(sum(x['different_bytes'] for x in counts),len(positions))
                    expected=[0]*3
                    for i in positions:
                        cell=i//7
                        expected[cell%3 if layout=='row_major' else cell//5]+=1
                    self.assertEqual([x['different_bytes'] for x in counts],expected)

    def test_header_changed_offsets(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=Path(t)/'a',Path(t)/'b';fixture(a);fixture(b)
            raw=bytearray(b.read_bytes());raw[4]=5;raw[40]=7;b.write_bytes(raw)
            self.assertEqual(compare(a,b)['header_changed_offsets'],[4,40])

    def test_invalid_block_type(self):
        with self.assertRaises(ValueError):compare('a','b',block_size=1.5)
